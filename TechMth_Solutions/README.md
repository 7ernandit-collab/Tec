# TechMth Solutions
## Automatización para la Coordinación de Titulación · TecNM Campus Matehuala

Sistema en Python que atiende a los egresados por **WhatsApp, Telegram, correo (Gmail y
Outlook) y llamadas**:
- Resuelve sus dudas sobre el proceso de titulación integral por residencia profesional.
- Les dice **qué ya tienen y qué les falta** para titularse.
- Les indica cuál es su siguiente paso.

Todo se responde por mensaje de texto, y lo que se recibe se guarda **únicamente en un archivo
de Excel**, separado por hojas. Ese archivo solo lo consulta la Coordinación.

> En esta versión los canales están **simulados**: se prueba todo desde la ventana, sin
> cuentas externas.

---

## 1. Instalación y uso

Requiere Python 3.10 o más reciente.

```bash
cd TechMth_Solutions
python -m pip install -r requirements.txt
python main.py            # aplicación de escritorio
python main.py --web      # página web en http://localhost:8550
python main.py --consola  # versión en la terminal
```

**Para publicarla con un enlace** (demostración en GitHub Pages y versión real en Render),
sigue **GUIA_PUBLICACION.md**.

### Portal de egresados (primera pantalla)
1. El egresado escribe su **número de control**. Para probar, usa el de ejemplo **24660999**.
2. Si es nuevo, llena sus datos en el mismo orden que la tabla Alumno: Nº Control, Nombre
   Completo, Carrera, Correo Institucional, Correo Personal y Teléfono.
3. Los confirma en una vista igual a la tabla de Excel, y se guardan con ese formato.
4. Si ya estaba registrado, puede **entrar** o **actualizar sus datos**.

Al pie del portal está el **Acceso Coordinación**, protegido con contraseña. Solo sirve
para descargar el Excel: la página nunca muestra los datos.

### Después de entrar
- **Inicio**
  - Banner con el logo de TechMth Solutions.
  - **Mi avance de titulación**: barra de progreso, «Lo que ya tienes», «Lo que te falta»
    y el siguiente paso.
  - Tarjetas de los canales de atención.
- **WhatsApp · Telegram · Correo · Llamadas**: cada canal en su propia sección, con preguntas
  frecuentes de un toque. Las llamadas se contestan por texto.
- **Panel «Mi avance»**: en computadora queda fijo a la derecha; en tableta y celular se
  desliza desde el borde cuando hace falta.

### Diseño skeuomórfico
- **Encabezado:** textura de piel azul marino con filo de luz.
- **Superficies:** tarjetas como hojas de papel con sombra real, y el área de conversación
  hundida en la página.
- **Botones y globos:** botones con brillo y relieve que se levantan al pasar el mouse;
  globos de chat tipo vidrio.
- **Barra de progreso:** con volumen.
- **Barra de navegación:** **solo con los íconos** (Inicio, WhatsApp, Telegram, Correo y
  Llamadas) en mosaicos con relieve. El nombre aparece al pasar el mouse.
- **Logos institucionales:** el **TecNM** y el **Instituto Tecnológico de Matehuala** van en
  una placa en el encabezado, el portal, el Inicio y el Acceso Coordinación.

### Se adapta a cualquier pantalla
- **Computadora** (≥ 1100 px): barra lateral de íconos, contenido y Mi avance fijo.
- **Tableta** (≥ 720 px): barra lateral de íconos más compacta.
- **Celular**: barra inferior de íconos y portal en una sola columna.

## 2. El archivo de Excel

En `config.json` indicas dónde está el archivo:

```json
"ruta_excel": "C:/Users/TuUsuario/OneDrive/Titulacion/Titulacion_Bot.xlsx"
```

Si lo pones dentro de tu carpeta de **OneDrive**, el archivo se sube solo a la nube. Puedes
usar tu Excel actual: el sistema reconoce las hojas **Alumno**, **Requisitos** y **No Adeudo**,
aunque el encabezado diga «Nº Comtrol». Las hojas que falten las agrega solo.

| Hoja | Quién la llena | Contenido |
|---|---|---|
| Alumno | Portal y Coordinación | Nº Control, nombre, carrera, correos y teléfono (el sistema agrega a quien se registra) |
| Requisitos | Coordinación | Créditos, servicio social, inglés, listo para titular (Si/No) |
| No Adeudo | Coordinación | Las 5 áreas (Si = ya firmó) |
| Mensajes | Sistema | Cada mensaje de WhatsApp, Telegram o correo, con la respuesta del sistema |
| Llamadas | Sistema | Cada llamada: número, duración, lo que dijo y el texto que se le envió |
| Pendientes | Sistema | Casos para una persona: preguntas que el sistema no entendió, solicitudes de atención y alertas de seguridad |

**Cambios a tu Excel actual**
- A la hoja **No Adeudo** le faltaba el número de control, por eso no se podía saber de qué
  alumno era cada fila. El sistema le agrega las columnas «Nº Control» y «Nombre del
  Estudiante». Completa esos datos en las filas que ya tenías.
- En el Excel que crea el sistema (`datos/Titulacion_Bot.xlsx`), el encabezado «Nº Comtrol» queda
  como «Nº Control».

**Cuidados**
- El primer arranque de cada día se guarda una copia de respaldo `…_respaldo_AAAAMMDD.xlsx`.
- Si el Excel está **abierto en Excel de escritorio**, Windows no deja escribir en él. El bot
  sigue contestando y guarda los registros cuando cierras el archivo; reintenta cada 20
  segundos. Si sales del sistema con el archivo todavía abierto, lo pendiente se guarda en
  `…_pendientes_FECHA.xlsx`.
- Abrir el archivo en **Excel en línea** (OneDrive web) no lo bloquea. Aun así, evita editar
  la misma fila mientras el sistema escribe.

## 3. Qué resuelve la atención automatizada

- **Responder dudas** (reglas locales, sin internet y sin costo): requisitos, pasos del
  trámite, documentos del expediente, carta de no adeudo, constancia, pago, fecha del acto,
  qué pasa si no se aprueba, tiempos, inglés, servicio social, créditos y contacto.
  - Entiende faltas de ortografía y abreviaturas («q», «xq», «ocupo», «requisistos»).
  - Responde varias preguntas en un mismo mensaje.
  - Varía sus frases y saluda según la hora del día.
- **Menú rápido**: se puede contestar con un número del 1 al 8.
- **Qué tienes y qué te falta** (opción 6): lee Requisitos y No Adeudo y responde lo que ya
  tiene, lo que le falta y el siguiente paso (en No Adeudo, «Si» = el área ya firmó). Por
  seguridad, solo da el estatus si el mensaje llega del teléfono o correo registrado en la
  hoja Alumno.
- **Registrar y actualizar datos** (opción 7):
  - Pide número de control, nombre, carrera y correos.
  - Toma el teléfono del WhatsApp y sugiere el correo institucional `L+número@matehuala.tecnm.mx`.
  - Crea las filas en Alumno, Requisitos y No Adeudo.
  - No sobrescribe el registro de otra persona.
- **Llamadas**: se registran en la hoja Llamadas y se contestan con un **mensaje de texto**
  al mismo número. Si la persona dijo algo (transcripción), le responde esa duda; si no,
  le manda el menú.
- **Correos**:
  - Ignora el historial citado.
  - Contesta con «Re: asunto», saludo y firma.
  - Quita el formato de WhatsApp (los asteriscos).
- **Pasar a una persona** (opción 8, o si no entiende): deja el caso en la hoja Pendientes.

## 4. Cambiar las respuestas

Todo lo que responde la Coordinación está en `base_conocimiento.json`. No hace falta tocar código:
- **palabras**: frases que activan cada tema, con un peso. Escríbelas sin acentos.
- **respuestas**: una o varias variantes. El sistema elige una al azar.
- **contacto**, **carreras** y **menu**: datos de la Coordinación, claves de carrera y
  opciones del menú.

En la base no puse costos ni horarios, porque no aparecen en tus entregas. Si los
confirmas con la Coordinación, agrégalos en las respuestas de «pago» y «contacto».

## 5. Pruebas

```bash
python -m unittest discover pruebas
```

Son 21 pruebas, entre ellas:
- Preguntas escritas con lenguaje natural, una de ellas con falta de ortografía.
- Dos preguntas en un solo mensaje.
- Estatus bloqueado cuando se pide desde un contacto distinto al registrado.
- Registro completo y protección contra sobrescribir el registro de otra persona.
- Llamadas que se contestan por texto, correo con historial citado y casos que se pasan a
  una persona.
- Registro desde el portal con el formato de tu tabla y actualización parcial.
- Respaldo del Excel en GitHub (subida y descarga).
- Un Excel como el tuyo (con «Nº Comtrol» y la fila 2 vacía) y un Excel bloqueado porque
  está abierto.

## 6. Siguiente paso: conectar los canales reales

El sistema recibe un `MensajeEntrante(canal, remitente, texto, asunto, …)` y devuelve una
`Respuesta(canal, para, texto, asunto)` (archivo `bot/canales.py`). Para pasar del
simulador a producción, cada conector solo convierte lo que recibe en un `MensajeEntrante`
y envía la `Respuesta`:

| Canal | Servicio sugerido |
|---|---|
| WhatsApp | Twilio o Meta WhatsApp Cloud API (webhook) |
| Telegram | Bot API de Telegram (gratuita): webhook o lectura periódica de mensajes |
| Gmail / Outlook | IMAP para leer y SMTP para responder; Outlook y Microsoft 365 suelen requerir OAuth |
| Llamadas | Twilio Voice: registra la llamada y transcribe lo que dijo, y el sistema responde por WhatsApp |

## 7. Estructura

```
main.py                  arranque (escritorio, --web, --consola, navegador)
config.json              ruta del Excel
base_conocimiento.json   temas, frases y respuestas del sistema
bot/texto.py             limpieza de texto y extracción de datos
bot/nlu.py               detección de intenciones (reglas con pesos y coincidencia aproximada)
bot/motor.py             conversación, estatus, registro y guardado
bot/excel.py             lectura y escritura del Excel por hojas y tablas
bot/canales.py           mensajes de entrada/salida y formato por canal
bot/ui.py                portal de egresados, Inicio, canales y panel Mi avance (Flet)
bot/respaldo_github.py   respaldo del Excel en un repositorio privado de GitHub
GUIA_PUBLICACION.md      cómo publicar en GitHub Pages y Render
render.yaml              configuración del servidor en Render
.github/workflows/       publicación automática en GitHub Pages
bot/avance.py            cálculo de lo que el egresado tiene y lo que le falta
bot/registro.py          validación y guardado de los datos del portal
bot/consola.py           simulador en la terminal
pruebas/                 pruebas automáticas
```
