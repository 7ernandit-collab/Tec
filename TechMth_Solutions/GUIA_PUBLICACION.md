# Guía de publicación · TechMth Solutions

Hay dos enlaces:

| | Demostración | Versión real |
|---|---|---|
| Dónde | GitHub Pages (`https://TU-USUARIO.github.io/techmth-solutions/`) | Render (`https://techmth-solutions.onrender.com`) |
| Cómo funciona | Python corre dentro del navegador | Python corre en un servidor |
| Datos | Ficticios; se quedan en el navegador de quien la abre | Llegan todos al mismo Excel |
| Para qué | Presentar el proyecto | Que los egresados la usen |

> **Importante.** El repositorio del código es **público**, así que nunca subas el Excel
> con datos de egresados. El archivo `.gitignore` ya bloquea `datos/` y los `.xlsx`.

---

## Paso 1 · Subir el código a GitHub

1. Entra a GitHub y crea un repositorio **público** llamado `techmth-solutions`. Déjalo
   vacío, sin README.
2. En la página del repositorio elige **Add file → Upload files**.
3. Arrastra **todo el contenido** de la carpeta `TechMth_Solutions`, incluida la carpeta
   oculta `.github`. Pulsa **Commit changes**.
   - Si la carpeta `.github` no se ve en Windows, actívala en el Explorador con
     **Vista → Mostrar → Elementos ocultos**.
   - Otra opción es instalar GitHub Desktop y publicar la carpeta desde ahí.

## Paso 2 · Activar la demostración en GitHub Pages

1. En el repositorio entra a **Settings → Pages**.
2. En **Source** elige **GitHub Actions**.
3. Ve a la pestaña **Actions**. Verás el proceso «Demostración en GitHub Pages»
   ejecutándose; tarda unos 3 minutos. Si no arrancó, ábrelo y pulsa **Run workflow**.
4. Cuando termine, el enlace aparece en **Settings → Pages**:
   `https://TU-USUARIO.github.io/techmth-solutions/`

La primera vez que se abre tarda unos segundos, mientras el navegador carga Python. Para
probarla, entra con el número de control de ejemplo **24660999**.

## Paso 3 · Crear el repositorio privado para el Excel

En Render el disco se borra cada vez que el servidor se reinicia o se duerme. Para no
perder los registros, la app guarda una copia del Excel en un repositorio **privado**.

1. En GitHub crea un repositorio **privado** llamado `techmth-datos`. Márcalo con
   **Add a README file** para que no quede vacío.
2. Crea un token:
   1. Entra a tu foto → **Settings → Developer settings → Personal access tokens →
      Fine-grained tokens → Generate new token**.
   2. En **Repository access** elige *Only select repositories* → `techmth-datos`.
   3. En **Permissions → Repository permissions → Contents** elige **Read and write**.
   4. Genera el token y **cópialo**: solo se muestra una vez.

## Paso 4 · Publicar la versión real en Render

1. Crea una cuenta en <https://render.com> entrando con tu cuenta de GitHub.
2. Elige **New → Blueprint** y selecciona el repositorio `techmth-solutions`. Render lee
   el archivo `render.yaml`.
3. Render te pedirá tres valores:
   - `COORD_CLAVE`: la contraseña del **Acceso Coordinación**. Inventa una segura.
   - `GITHUB_TOKEN`: el token del paso 3.
   - `GITHUB_REPO_DATOS`: `TU-USUARIO/techmth-datos`
4. Pulsa **Apply**. Cuando el estado diga *Live*, el enlace queda así:
   `https://techmth-solutions.onrender.com`

**Notas sobre el plan gratuito de Render**
- Si nadie entra en 15 minutos, el servidor se duerme; la siguiente visita tarda cerca de
  un minuto en abrir.
- El Excel no se pierde: al despertar, la app lo descarga de `techmth-datos`, y después de
  cada registro lo vuelve a subir (cada 20 segundos como máximo).

## Paso 5 · Ver los datos (Coordinación)

Hay dos formas:
- En la página real, pulsa **Acceso Coordinación** al pie del portal, escribe la contraseña
  (`COORD_CLAVE`) y pulsa **Descargar Excel**. El enlace de descarga vence en 15 minutos.
- O abre el repositorio privado `techmth-datos` en GitHub y descarga `Titulacion_Bot.xlsx`.

En el Excel llenas las hojas **Requisitos** y **No Adeudo** («Si» = cumple o ya firmó).
Para que el sistema use tus cambios, sube el archivo editado al repositorio privado y
reinicia el servicio en Render (**Manual Deploy → Restart service**).

## Actualizar la app

Cada vez que cambies algo del código y lo subas a GitHub, la demostración se vuelve a
publicar sola y Render vuelve a desplegar la versión real. Los datos no se pierden porque
están en el repositorio privado.
