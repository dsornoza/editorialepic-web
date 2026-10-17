#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPIC · Alta de un integrante del Consejo Editorial en un solo paso.

Hace, desde la raíz del repositorio:
  1. Agrega la tarjeta en /consejo-editorial/ y /en/editorial-board/ (institución, país, ORCID).
  2. Crea la bandera assets/img/flags/<iso>.png si no existe (flag-icons, MIT).
  3. Registra el certificado CE en certificados.json y genera el QR/sello en inglés.
  4. Genera el certificado Word en inglés en _plantillas/emitidos/ a partir de la plantilla 08.
No hace commit ni push: eso se hace después de revisar.

Ejemplo:
  python3 _herramientas/nuevo_miembro.py --nombre "Ann T. Kirugumi" \
      --institucion "Dedan Kimathi University of Technology" \
      --pais-es Kenia --pais-en Kenya --iso ke \
      --orcid 0000-0002-5665-6821 \
      --area-en "International business and university internationalization"
"""
import argparse, datetime, html, json, os, re, shutil, subprocess, sys, tempfile, unicodedata, urllib.request

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import certificado as cert  # noqa: E402

FLAGS = os.path.join(RAIZ, "assets", "img", "flags")
PAGINAS = {
    "es": os.path.join(RAIZ, "consejo-editorial", "index.html"),
    "en": os.path.join(RAIZ, "en", "editorial-board", "index.html"),
}
PLANTILLA = os.path.join(RAIZ, "_plantillas", "08_Certificate_Editorial_Board_Member_EN.docx")
EMITIDOS = os.path.join(RAIZ, "_plantillas", "emitidos")
MESES = ["January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"]


def fecha_en(f):
    return f"{f.day} {MESES[f.month - 1]} {f.year}"


def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def asegurar_bandera(iso):
    destino = os.path.join(FLAGS, f"{iso}.png")
    if os.path.exists(destino):
        return False
    from PIL import Image
    url = f"https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.2.3/flags/4x3/{iso}.svg"
    tmp = tempfile.mkdtemp()
    try:
        svg = os.path.join(tmp, f"{iso}.svg")
        with urllib.request.urlopen(url, timeout=30) as r, open(svg, "wb") as f:
            f.write(r.read())
        subprocess.run(["qlmanage", "-t", "-s", "512", "-o", tmp, svg], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        img = Image.open(os.path.join(tmp, f"{iso}.svg.png")).convert("RGBA")
        # qlmanage deja la bandera sobre un lienzo: recortar al contenido de proporción 4:3.
        w, h = img.size
        fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fondo.alpha_composite(img)
        px = fondo.convert("RGB")
        caja = px.point(lambda v: 0 if v > 250 else 255).convert("L").getbbox() or (0, 0, w, h)
        img = img.crop(caja).resize((64, 48), Image.LANCZOS)
        os.makedirs(FLAGS, exist_ok=True)
        img.save(destino, optimize=True)
        print(f"  Bandera creada: assets/img/flags/{iso}.png (revísala: banderas con blanco en el borde pueden recortarse mal)")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tarjeta(nombre, inst, pais, iso, orcid, alt):
    e = html.escape
    return f'''          <li class="miembro">
            <img class="miembro-bandera" src="/assets/img/flags/{iso}.png" alt="{e(alt)}" width="32" height="24">
            <h3 class="miembro-nombre">{e(nombre)}</h3>
            <p class="miembro-inst">{e(inst)}</p>
            <p class="miembro-pais">{e(pais)}</p>
            <a class="miembro-orcid" href="https://orcid.org/{orcid}" rel="noopener">ORCID {orcid}</a>
          </li>
'''


def agregar_tarjeta(idioma, bloque, nombre):
    ruta = PAGINAS[idioma]
    s = open(ruta, encoding="utf-8").read()
    if nombre in s:
        sys.exit(f"{nombre} ya aparece en {os.path.relpath(ruta, RAIZ)}. No se duplica.")
    marca = "<!-- PLANTILLA DE INTEGRANTE" if idioma == "es" else "<!-- MEMBER TEMPLATE"
    i = s.find(marca)
    if i < 0:
        sys.exit(f"No encuentro el comentario de plantilla en {ruta}.")
    i = s.rfind("\n", 0, i) + 1  # inicio de la línea del comentario
    open(ruta, "w", encoding="utf-8").write(s[:i] + bloque + s[i:])


def quitar_sombreado(run):
    for shd in run._r.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd"):
        shd.getparent().remove(shd)


def reemplazar(doc_parrafos, viejo, nuevo):
    n = 0
    for p in doc_parrafos:
        for r in p.runs:
            # Solo los marcadores sombreados; las etiquetas (p. ej. «Field of knowledge») se quedan.
            if r.text == viejo and r._r.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd"):
                r.text = nuevo
                quitar_sombreado(r)
                n += 1
    return n


def generar_docx(cid, a, f):
    import docx
    from docx.shared import Cm
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    d = docx.Document(PLANTILLA)
    parrafos = list(d.paragraphs)
    celdas = []
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                celdas.extend(c.paragraphs)
    todos = parrafos + celdas
    reemplazar(todos, "EPIC-YYYY-CE-NNNN", cid)
    reemplazar(todos, "Full name of the member", a.nombre)
    reemplazar(todos, "Full name", a.nombre)
    reemplazar(todos, "Institution, Country", f"{a.institucion}, {a.pais_en}")
    reemplazar(todos, "Field of knowledge", a.area_en)
    reemplazar(todos, "0000-0000-0000-0000", a.orcid)
    reemplazar(todos, "day Month year", fecha_en(f))
    reemplazar(todos, "Signer name", a.firmante)
    reemplazar(todos, "Title", a.cargo)
    # Sello de verificación en la caja punteada.
    sello = os.path.join(RAIZ, "_qr", f"{cid}_sello_en.png")
    caja = d.tables[-1].rows[0].cells[1]
    for p in caja.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    p0 = caja.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    p0.add_run().add_picture(sello, width=Cm(3.6))
    tcPr = caja._tc.get_or_add_tcPr()
    for b in tcPr.findall(qn("w:tcBorders")):
        tcPr.remove(b)
    borders = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    # tcBorders debe ir antes de shd/vAlign según el esquema.
    despues = [qn("w:shd"), qn("w:noWrap"), qn("w:tcMar"), qn("w:textDirection"), qn("w:tcFitText"), qn("w:vAlign")]
    pos = next((i for i, ch in enumerate(tcPr) if ch.tag in despues), len(tcPr))
    tcPr.insert(pos, borders)
    # Comprobación: no deben quedar marcadores.
    restos = [t for t in ("YYYY", "NNNN", "Full name", "Signer name", "Paste the verification", "day Month year")
              if any(t in r.text for p in d.paragraphs for r in p.runs)
              or any(t in r.text for tb in d.tables for row in tb.rows for c in row.cells for p in c.paragraphs for r in p.runs)]
    if restos:
        sys.exit(f"Quedaron marcadores sin reemplazar en el Word: {restos}")
    os.makedirs(EMITIDOS, exist_ok=True)
    apellido = sin_acentos(a.nombre.split()[-1])
    nombre_arch = re.sub(r"[^A-Za-z0-9]+", "_", sin_acentos(a.nombre)).strip("_")
    salida = os.path.join(EMITIDOS, f"{cid}_{nombre_arch}_EN.docx")
    d.save(salida)
    return salida


def main():
    p = argparse.ArgumentParser(description="Alta de integrante del Consejo Editorial (sitio + certificado).")
    p.add_argument("--nombre", required=True)
    p.add_argument("--institucion", required=True, help="Solo la institución, sin país")
    p.add_argument("--pais-es", required=True)
    p.add_argument("--pais-en", required=True)
    p.add_argument("--iso", required=True, help="Código ISO de 2 letras del país (ke, mx, ec...)")
    p.add_argument("--orcid", required=True, help="0000-0000-0000-0000")
    p.add_argument("--area-en", required=True, help="Campo de conocimiento (solo va en el certificado, en inglés)")
    p.add_argument("--fecha", default=datetime.date.today().isoformat(), help="AAAA-MM-DD (por defecto, hoy)")
    p.add_argument("--firmante", default="Dr. Diego Sornoza Parrales")
    p.add_argument("--cargo", default="Editorial Manager")
    a = p.parse_args()

    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", a.orcid):
        sys.exit("ORCID con formato inválido (0000-0000-0000-0000).")
    a.iso = a.iso.lower()
    if not re.fullmatch(r"[a-z]{2}", a.iso):
        sys.exit("--iso debe ser un código de 2 letras.")
    try:
        f = datetime.date.fromisoformat(a.fecha)
    except ValueError:
        sys.exit("La fecha debe tener el formato AAAA-MM-DD.")
    if not os.path.exists(PLANTILLA):
        sys.exit(f"Falta la plantilla {PLANTILLA}")

    ruta_json = os.path.join(RAIZ, "certificados.json")
    datos = cert.cargar(ruta_json)
    if any(c.get("titular") == a.nombre for c in datos.get("certificados", [])):
        sys.exit(f"{a.nombre} ya tiene un certificado CE registrado. No se duplica.")
    for idioma in PAGINAS:
        if a.nombre in open(PAGINAS[idioma], encoding="utf-8").read():
            sys.exit(f"{a.nombre} ya aparece en el sitio. No se duplica.")

    print("1/4 Bandera")
    if not asegurar_bandera(a.iso):
        print(f"  Ya existe assets/img/flags/{a.iso}.png")

    print("2/4 Tarjetas del sitio")
    agregar_tarjeta("es", tarjeta(a.nombre, a.institucion, a.pais_es, a.iso, a.orcid, a.pais_es), a.nombre)
    agregar_tarjeta("en", tarjeta(a.nombre, a.institucion, a.pais_en, a.iso, a.orcid, a.pais_en), a.nombre)

    print("3/4 Registro del certificado y QR (inglés)")
    datos["certificados"].append({})  # reserva de lugar para calcular el id con las reglas del script
    datos["certificados"].pop()
    cid = cert.siguiente_id(datos["certificados"], f.year, "CE", datos.get("anulados", []))
    datos["certificados"].append({"id": cid, "tipo": cert.TIPOS["CE"], "fecha": f.isoformat(), "titular": a.nombre})
    cert.guardar(ruta_json, datos)
    res = cert.generar_qr(cid, os.path.join(RAIZ, "_qr"), "en")
    if not res:
        sys.exit("No se pudo generar el QR (instala: pip install --user segno pillow).")

    print("4/4 Certificado Word (inglés)")
    docx_ruta = generar_docx(cid, a, f)

    print("\nListo.")
    print(f"  Código:      {cid}")
    print(f"  Verificación: {cert.url_verificacion(cid, 'en')}")
    print(f"  Word:        {os.path.relpath(docx_ruta, RAIZ)}")
    print("  Pendiente:   revisar, exportar el Word a PDF, y publicar (commit y push de certificados.json, las dos páginas y la bandera).")


if __name__ == "__main__":
    main()
