#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPIC · Registro de certificados y generación de QR.

Uso (desde la raíz del repositorio):
  python3 _herramientas/certificado.py nuevo --tipo AR --titulo "Título" --autores "Ana Pérez; Luis Gómez" \
          --isbn 978-9942-00000-0-0 --doi 10.5281/zenodo.0000000
  python3 _herramientas/certificado.py listar
  python3 _herramientas/certificado.py anular EPIC-2026-AR-0001

Qué hace "nuevo":
  1. Asigna el siguiente código libre: EPIC-AAAA-TT-NNNN
  2. Lo registra en certificados.json (el que lee /verificar/).
  3. Crea en _qr/ el QR (PNG y SVG) y el "sello de verificación" (PNG) para pegar en el documento.
Después hay que publicar certificados.json (commit y push).
"""
import argparse, datetime, json, os, re, sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITIO = "https://editorialepic.com"

TIPOS = {
    "AC": "Carta de aceptación",
    "AR": "Certificado de arbitraje",
    "PU": "Carta de publicación",
    "RV": "Certificado de revisión por pares",
    "CE": "Certificado de integrante del Consejo Editorial",
}
PATRON = re.compile(r"^EPIC-(\d{4})-(AC|AR|PU|RV|CE)-(\d{4})$")


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def guardar(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


def siguiente_id(certs, anio, tipo, anulados=()):
    """Siguiente código libre. Los anulados cuentan como usados: un código nunca se reutiliza."""
    ids = [str(c.get("id", "")) for c in certs] + [str(x) for x in anulados]
    usados = [int(m.group(3)) for i in ids
              if (m := PATRON.match(i)) and m.group(1) == str(anio) and m.group(2) == tipo]
    return f"EPIC-{anio}-{tipo}-{(max(usados) + 1) if usados else 1:04d}"


def url_verificacion(cid):
    return f"{SITIO}/verificar/?id={cid}"


def generar_qr(cid, carpeta):
    try:
        import segno
    except ImportError:
        print("  (No se generó el QR: falta la librería. Instala con: pip install --user segno)")
        return None
    os.makedirs(carpeta, exist_ok=True)
    qr = segno.make(url_verificacion(cid), error="q", micro=False)
    png = os.path.join(carpeta, f"{cid}.png")
    svg = os.path.join(carpeta, f"{cid}.svg")
    qr.save(png, scale=12, border=3, dark="#1B2A49", light="#FFFFFF")
    qr.save(svg, scale=12, border=3, dark="#1B2A49", light="#FFFFFF")
    sello = crear_sello(cid, png, carpeta)
    return png, svg, sello


def _fuente(tam, negrita=False):
    from PIL import ImageFont
    candidatas = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if negrita else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for ruta in candidatas:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tam, index=1 if (negrita and ruta.endswith(".ttc")) else 0)
            except Exception:
                continue
    return ImageFont.load_default()


def crear_sello(cid, png_qr, carpeta):
    """QR + texto, listo para pegar en Word/Canva (esquina inferior derecha, mínimo 2,5 cm de ancho)."""
    from PIL import Image, ImageDraw
    qr = Image.open(png_qr).convert("RGB")
    # El QR se pega sin reescalar (módulos de tamaño entero) para que se lea bien al imprimirlo.
    ancho = max(700, qr.width + 80)
    alto = qr.height + 20 + 190
    lienzo = Image.new("RGB", (ancho, alto), "#FFFFFF")
    lienzo.paste(qr, ((ancho - qr.width) // 2, 10))
    base = qr.height + 32
    d = ImageDraw.Draw(lienzo)
    azul = "#1B2A49"

    def centrado(texto, y, fuente, color=azul):
        w = d.textlength(texto, font=fuente)
        d.text(((ancho - w) / 2, y), texto, font=fuente, fill=color)

    centrado("Verifica este documento", base, _fuente(34, True))
    centrado("editorialepic.com/verificar", base + 48, _fuente(30), "#5B6572")
    centrado(f"Código {cid}", base + 98, _fuente(32, True))
    ruta = os.path.join(carpeta, f"{cid}_sello.png")
    lienzo.save(ruta, optimize=True)
    return ruta


def main():
    p = argparse.ArgumentParser(description="Registro de certificados de EPIC")
    p.add_argument("--json", default=os.path.join(RAIZ, "certificados.json"), help="ruta de certificados.json")
    p.add_argument("--qr", default=os.path.join(RAIZ, "_qr"), help="carpeta de salida de los QR")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("nuevo", help="registra un certificado y genera su QR")
    n.add_argument("--tipo", required=True, choices=sorted(TIPOS), help="AC, AR, PU, RV o CE")
    n.add_argument("--titular", default="", help="Solo CE: nombre del integrante del Consejo")
    n.add_argument("--titulo", default="")
    n.add_argument("--autores", default="", help='separados por ";"')
    n.add_argument("--fecha", default=datetime.date.today().isoformat(), help="AAAA-MM-DD")
    n.add_argument("--isbn", default="")
    n.add_argument("--doi", default="")

    sub.add_parser("listar", help="muestra los certificados registrados")
    a = sub.add_parser("anular", help="elimina un certificado (deja de verificarse)")
    a.add_argument("id")

    args = p.parse_args()
    datos = cargar(args.json)
    certs = datos.setdefault("certificados", [])

    if args.cmd == "listar":
        if not certs:
            print("No hay certificados registrados.")
        for c in certs:
            print(f'{c["id"]}  {c.get("fecha", "")}  {c.get("tipo", "")}  {c.get("titulo") or c.get("titular", "")}')
        return

    if args.cmd == "anular":
        antes = len(certs)
        quitado = [c for c in certs if str(c.get("id")).lower() == args.id.lower()]
        if not quitado:
            sys.exit(f"No existe el código {args.id}.")
        datos["certificados"] = [c for c in certs if c not in quitado]
        # El código queda reservado: no se volverá a asignar.
        datos.setdefault("anulados", []).append(quitado[0]["id"])
        guardar(args.json, datos)
        print(f"Anulado {args.id}. Queda reservado (no se reutilizará). Publica certificados.json para que deje de verificarse.")
        return

    # nuevo
    try:
        fecha = datetime.date.fromisoformat(args.fecha)
    except ValueError:
        sys.exit("La fecha debe tener el formato AAAA-MM-DD.")
    if args.tipo == "RV" and (args.titulo or args.autores or args.isbn or args.doi):
        sys.exit("Certificado de revisión (RV): por la política de confidencialidad no se registra título, "
                 "autores, ISBN ni DOI. Solo tipo y fecha.")
    if args.tipo == "CE":
        if not args.titular:
            sys.exit("Certificado de integrante (CE): falta --titular.")
        if args.titulo or args.autores or args.isbn or args.doi:
            sys.exit("Certificado de integrante (CE): solo se registra titular y fecha.")
    elif args.titular:
        sys.exit("--titular solo se usa con el tipo CE.")
    if args.tipo not in ("RV", "CE") and not args.titulo:
        sys.exit("Falta --titulo.")

    cid = siguiente_id(certs, fecha.year, args.tipo, datos.get("anulados", []))
    registro = {"id": cid, "tipo": TIPOS[args.tipo], "fecha": fecha.isoformat()}
    if args.titular:
        registro["titular"] = args.titular
    if args.titulo:
        registro["titulo"] = args.titulo
    autores = [x.strip() for x in args.autores.split(";") if x.strip()]
    if autores:
        registro["autores"] = autores
    if args.isbn:
        registro["isbn"] = args.isbn
    if args.doi:
        registro["doi"] = args.doi
    certs.append(registro)
    guardar(args.json, datos)

    print(f"Registrado: {cid}  ({TIPOS[args.tipo]})")
    print(f"  URL de verificación: {url_verificacion(cid)}")
    res = generar_qr(cid, args.qr)
    if res:
        print(f"  QR (PNG):    {res[0]}")
        print(f"  QR (SVG):    {res[1]}")
        print(f"  Sello listo: {res[2]}")
    print("  Siguiente paso: publicar certificados.json (commit y push).")


if __name__ == "__main__":
    main()
