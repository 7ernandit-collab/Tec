"""TechMth Solutions · Automatización para la Coordinación de Titulación (TecNM Campus Matehuala)

Uso:
    python main.py              aplicación de escritorio
    python main.py --web        página web (servidor; en Render se usa este modo)
    python main.py --consola    versión en la terminal

Variables de entorno (servidor):
    PORT                 puerto (Render lo pone solo)
    COORD_CLAVE          contraseña del Acceso Coordinación (para descargar el Excel)
    GITHUB_TOKEN         \\  respaldo del Excel en un repositorio PRIVADO de GitHub
    GITHUB_REPO_DATOS    /   (ver GUIA_PUBLICACION.md)
    DATOS_DE_EJEMPLO     1 para cargar los egresados ficticios de ejemplo
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from bot.ejemplo import cargar_ejemplo
from bot.excel import AlmacenExcel
from bot.motor import Bot

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
EN_NAVEGADOR = sys.platform == "emscripten"      # demostración en GitHub Pages


def crear_bot(con_respaldo: bool = False):
    ruta = Path(CONFIG["ruta_excel"]).expanduser()
    if not ruta.is_absolute():
        ruta = BASE / ruta
    respaldo = None
    if con_respaldo:
        from bot.respaldo_github import RespaldoGitHub
        respaldo = RespaldoGitHub.desde_entorno(ruta)
        if respaldo:
            respaldo.descargar()             # recupera el Excel antes de abrirlo
    almacen = AlmacenExcel(ruta)
    if respaldo:
        almacen.al_guardar.append(respaldo.programar)
    ejemplo = os.environ.get("DATOS_DE_EJEMPLO")
    if (ejemplo == "1") or (ejemplo is None and CONFIG.get("cargar_datos_de_ejemplo")) or EN_NAVEGADOR:
        cargar_ejemplo(almacen)
    return Bot(almacen, BASE / "base_conocimiento.json"), respaldo


def ejecutar_flet(modo: str):
    import flet as ft

    from bot.ui import iniciar

    bot, respaldo = crear_bot(con_respaldo=(modo == "servidor"))
    # En el servidor la contraseña SOLO viene de la variable COORD_CLAVE (config.json es público en GitHub).
    if modo == "servidor":
        clave = os.environ.get("COORD_CLAVE", "")
        if not clave:
            print("⚠ Define la variable COORD_CLAVE: sin ella nadie puede entrar al Acceso Coordinación.",
                  file=sys.stderr)
    else:
        clave = os.environ.get("COORD_CLAVE") or CONFIG.get("clave_coordinacion", "")

    def principal(page):
        iniciar(page, bot, modo=modo, clave_coordinacion=clave, respaldo=respaldo, dir_assets=ASSETS)

    if modo == "servidor":
        puerto = int(os.environ.get("PORT", 8550))
        print(f"TechMth Solutions en http://0.0.0.0:{puerto}")
        ft.app(target=principal, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=puerto, assets_dir=str(ASSETS))
    else:
        ft.app(target=principal, assets_dir=str(ASSETS))


if EN_NAVEGADOR:                     # GitHub Pages: Python corre dentro del navegador
    ejecutar_flet("demo")
elif __name__ == "__main__":
    if "--consola" in sys.argv:
        from bot.consola import ejecutar
        ejecutar(crear_bot()[0])
    else:
        ejecutar_flet("servidor" if "--web" in sys.argv else "escritorio")
