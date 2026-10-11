# Certificados de EPIC: numeración, registro y QR

Esta carpeta no se publica en el sitio (las carpetas que empiezan con `_` no las sirve GitHub Pages).

## 1. Numeración de códigos

Formato: **`EPIC-AAAA-TT-NNNN`**

| Parte | Significado | Ejemplo |
|---|---|---|
| `AAAA` | Año de la fecha del documento | `2026` |
| `TT` | Tipo de documento | `AC`, `AR`, `PU`, `RV` |
| `NNNN` | Número correlativo, de 4 dígitos, **por año y por tipo** | `0001` |

| TT | Documento |
|---|---|
| `AC` | Carta de aceptación |
| `AR` | Certificado de arbitraje |
| `PU` | Carta de publicación |
| `RV` | Certificado de revisión por pares (para revisores) |
| `CE` | Certificado de integrante del Consejo Editorial |

Ejemplos: `EPIC-2026-AR-0001`, `EPIC-2026-PU-0014`, `EPIC-2027-RV-0003`.

Reglas:
- **Un código por documento.** Una obra genera tres: carta de aceptación, certificado de arbitraje y carta de publicación.
- Cada año el contador de cada tipo vuelve a `0001`.
- **Un código nunca se reutiliza**, ni siquiera si el certificado se anula (queda reservado en `certificados.json`, en la lista `anulados`).
- El código debe estar **escrito igual** en el documento, en el QR y en `certificados.json`.

## 2. Qué se registra y qué no

- Cartas y certificados de una obra (`AC`, `AR`, `PU`): título, autores, fecha, ISBN y DOI (si ya existen).
- **Certificados de integrante del Consejo (`CE`): solo titular y fecha** (`--titular "Nombre Apellido"`). El nombre ya es público en la página del Consejo; no se registran otros datos.
- **Certificados de revisión (`RV`): solo tipo y fecha.** No se registran título, autores, ISBN, DOI ni el nombre del revisor, porque las políticas dicen que la identidad de los revisores es confidencial y que el listado no se vincula con obras concretas. El script lo impide.
- `certificados.json` es público: cualquiera puede descargarlo.

## 3. Flujo para cada certificado

1. Registrar y generar el QR (desde la raíz del repositorio):

   ```
   python3 _herramientas/certificado.py nuevo --tipo AR \
       --titulo "Título de la obra" --autores "Ana Pérez; Luis Gómez" \
       --fecha 2026-11-15 --isbn 978-9942-00000-0-0 --doi 10.5281/zenodo.0000000
   ```

   Para un certificado de revisión: `... nuevo --tipo RV --fecha 2026-11-30`

2. El script imprime el código asignado y crea en `_qr/` tres archivos:
   - `EPIC-AAAA-TT-NNNN.png`: el QR solo.
   - `EPIC-AAAA-TT-NNNN.svg`: el QR en vectorial, para impresión.
   - `EPIC-AAAA-TT-NNNN_sello.png`: **el sello de verificación** (QR + texto + código), listo para pegar en el documento.
3. Pegar el sello en el certificado (ver sección 4) y escribir el mismo código en el texto del documento.
4. **Publicar `certificados.json`** (commit y push). El registro aparece en `/verificar/` en uno o dos minutos.
5. Probar: escanear el QR con un celular y comprobar que dice «Documento válido» y que los datos coinciden.

Para un documento en inglés, agrega `--idioma en`: el QR apunta a `/en/verify/` y el sello dice «Verify this document».
Para volver a generar el QR de un código ya registrado (por ejemplo, la versión en inglés):
`python3 _herramientas/certificado.py qr EPIC-2026-CE-0001 --idioma en`
(crea `..._en.png`, `..._en.svg` y `..._sello_en.png`).

Otros comandos:
- `python3 _herramientas/certificado.py listar` muestra los certificados registrados.
- `python3 _herramientas/certificado.py anular EPIC-2026-AR-0001` lo retira (pasa a «No encontrado») y reserva el código.

Requisitos: Python 3 con `segno` y `Pillow` (`pip install --user segno pillow`).

## 4. Plantilla de colocación del QR en el documento

El QR apunta a `https://editorialepic.com/verificar/?id=CÓDIGO`.

- **Ubicación:** esquina inferior derecha de la primera página, o junto a la firma. Siempre en el mismo lugar en todos los documentos.
- **Tamaño:** el sello mide **mínimo 2,5 cm de ancho** impreso (recomendado 3 a 3,5 cm). Menos se lee mal.
- **Margen:** deja al menos 0,5 cm libres alrededor. No pongas texto, líneas ni marcas de agua encima del QR.
- **Contraste:** el QR es azul tinta (`#1B2A49`) sobre fondo blanco. No lo inviertas ni lo pongas sobre color o foto.
- **No lo deformes:** conserva la proporción (cuadrado) al cambiar el tamaño.
- **Texto del sello:** «Verifica este documento · editorialepic.com/verificar · Código EPIC-AAAA-TT-NNNN». Si el documento se imprime sin QR legible, el código sirve para verificar a mano.
- **En Word o Canva:** inserta el PNG del sello como imagen, con «ajustar a texto: delante» y anclado a la página. Para impresión profesional, usa el SVG del QR.
- **En el texto del documento**, agrega una línea como: «Este documento puede verificarse en editorialepic.com/verificar con el código EPIC-AAAA-TT-NNNN».
