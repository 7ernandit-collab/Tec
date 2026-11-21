"""Interfaz de TechMth Solutions · Coordinación de Titulación (Flet, solo Python).

Estilo skeuomórfico: superficies tipo papel, encabezado con textura de piel, botones con
relieve y brillo, mosaicos de íconos con sombra real y barras de progreso con volumen.

El mismo código funciona como:
  • aplicación de escritorio         python main.py
  • página web en un servidor        python main.py --web   (Render u otro)
  • demostración en GitHub Pages     (Python corriendo en el navegador)

Pantallas: Portal de egresados → Inicio (Mi avance) · WhatsApp · Telegram · Correo · Llamadas.
Acceso de la Coordinación (con contraseña) solo para descargar el Excel.
El diseño se reacomoda según el ancho: computadora, tableta o celular.
"""
from __future__ import annotations

import hmac
import shutil
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import flet as ft

from . import avance, registro
from .canales import CANALES, MensajeEntrante
from .motor import Bot

# ------------------------------------------------------------------ identidad
AZUL, INDIGO, LAVANDA, TURQUESA, CREMA = "#000B3D", "#434B9B", "#8A93F0", "#2A9BAE", "#F5F2EA"
BLANCO, BORDE, SUAVE, ROJO, VERDE = "#FFFFFF", "#D8D1C2", "#5A5F7A", "#B3261E", "#1E9E5A"
LAVANDA_CLARO, TURQUESA_CLARO, VERDE_CLARO, NARANJA_CLARO = "#E8EAFD", "#DDF1F4", "#E9F6EE", "#FFF4E5"
EXCEL_VERDE, TABLA_ENC = "#107C41", "#1B5E85"
PAPEL = ("#FFFFFF", "#F1ECE2")            # superficie de papel
PIEL = ("#1C2770", "#0A1450", "#000B3D")  # piel azul marino del encabezado
I = ft.Icons

# Botones con relieve: (claro, medio, oscuro, borde)
RELIEVE = {
    "turquesa": ("#6FD0DE", "#2A9BAE", "#1C7C8D", "#17697A"),
    "azul": ("#4F5AB2", "#1F2A78", "#000B3D", "#00062A"),
    "verde": ("#6BD99A", "#1E9E5A", "#157A44", "#106236"),
    "excel": ("#4DB67D", "#107C41", "#0B5E31", "#084A26"),
    "claro": ("#FFFFFF", "#F4F0E8", "#E4DED1", "#C7BFAE"),
}

AMPLIA, MEDIA = 1100, 720
ANCHO_PANEL = 340

CANALES_UI = [
    # clave, imagen, nombre, descripción, color
    ("whatsapp", "canal_whatsapp.png", "WhatsApp", "Escríbenos por chat", "#25D366"),
    ("telegram", "canal_telegram.png", "Telegram", "Chat en Telegram", "#2AABEE"),
    ("correo", "canal_correo.png", "Correo", "Gmail u Outlook", "#EA4335"),
    ("llamadas", "canal_llamadas.png", "Llamadas", "Te respondemos por texto", TURQUESA),
]
VISTAS = [("inicio", "canal_inicio.png", "Inicio")] + [(c, img, n) for c, img, n, _, _ in CANALES_UI]
TEMAS = {
    "requisitos": "Requisitos", "proceso": "Pasos del trámite", "documentos": "Documentos",
    "no_adeudo": "Carta de no adeudo", "constancia": "Constancia", "pago": "Pago",
    "acto": "Acto protocolario", "reprobar": "Si no aprueba", "duracion": "Tiempos",
    "residencia": "Residencia", "ingles": "Inglés", "servicio_social": "Servicio social",
    "creditos": "Créditos", "contacto": "Contacto", "estatus": "Mi avance",
    "registro": "Mis datos", "humano": "Atención personal", "saludo": "Saludo",
    "despedida": "Despedida", "gracias": "Agradecimiento", "menu": "Menú",
    "no_entendido": "Turnada a la Coordinación", "llamada": "Llamada", "cancelar": "Cancelación",
}
SUGERIDAS = [("Requisitos", "¿Cuáles son los requisitos?"), ("Pasos", "¿Cuáles son los pasos del trámite?"),
             ("Documentos", "¿Qué documentos lleva el expediente?"),
             ("No adeudo", "¿Qué firmas lleva la carta de no adeudo?"), ("Pago", "¿Cuánto cuesta y cómo pago?"),
             ("Fecha del acto", "¿Cuándo es mi acto protocolario?"), ("¿Qué me falta?", "¿Qué me falta?"),
             ("Hablar con alguien", "Quiero hablar con una persona")]

EN_NAVEGADOR = sys.platform == "emscripten"   # demostración en GitHub Pages


def _modo(ancho: float) -> str:
    return "amplia" if ancho >= AMPLIA else "media" if ancho >= MEDIA else "angosta"


def _degradado(*colores, vertical=True):
    return ft.LinearGradient(begin=ft.alignment.top_center if vertical else ft.alignment.top_left,
                             end=ft.alignment.bottom_center if vertical else ft.alignment.bottom_right,
                             colors=list(colores))


def _sombras(profundidad=1.0):
    """Sombra de objeto físico: una cercana y marcada, otra lejana y difusa."""
    return [ft.BoxShadow(blur_radius=3, spread_radius=0, offset=ft.Offset(0, 2 * profundidad),
                         color=ft.Colors.with_opacity(0.22, "#1A1430")),
            ft.BoxShadow(blur_radius=18 * profundidad, spread_radius=-2, offset=ft.Offset(0, 9 * profundidad),
                         color=ft.Colors.with_opacity(0.20, "#1A1430"))]


def _sombra_texto(clara=False):
    return ft.TextStyle(shadow=ft.BoxShadow(blur_radius=1, offset=ft.Offset(0, 1 if clara else -1),
                                            color=ft.Colors.with_opacity(0.8 if clara else 0.45,
                                                                         BLANCO if clara else "#000000")))


def _relieve_hover(e):
    """Al pasar el mouse el objeto se levanta un poco; al salir vuelve."""
    e.control.scale = 1.03 if e.data == "true" else 1
    e.control.update()


# ======================================================================
#  Componentes skeuomórficos
# ======================================================================
def tarjeta(contenido, padding=20, col=None, borde=BORDE, fondo=None, **kw):
    """Hoja de papel: degradado suave, borde con luz arriba y sombra real."""
    return ft.Container(content=contenido, padding=padding, gradient=_degradado(*(fondo or PAPEL)),
                        border_radius=18, border=ft.border.all(1, borde), shadow=_sombras(), col=col, **kw)


def boton(texto, al_pulsar, icono=None, color="turquesa", expand=False, alto=50):
    """Botón con relieve: brillo arriba, sombra abajo y texto grabado."""
    if color not in RELIEVE:
        color = {VERDE: "verde", AZUL: "azul", EXCEL_VERDE: "excel"}.get(color, "turquesa")
    claro, medio, oscuro, borde = RELIEVE[color]
    texto_color = AZUL if color == "claro" else BLANCO
    contenido = [ft.Text(texto, size=15, weight=ft.FontWeight.BOLD, color=texto_color,
                         style=_sombra_texto(clara=color == "claro"))]
    if icono:
        contenido.insert(0, ft.Icon(icono, color=texto_color, size=20))
    cuerpo = ft.Container(
        ft.Stack([
            ft.Container(ft.Row(contenido, spacing=8, alignment=ft.MainAxisAlignment.CENTER, tight=not expand),
                         alignment=ft.alignment.center, padding=ft.padding.symmetric(horizontal=22),
                         top=0, bottom=0, left=0, right=0),
            # reflejo de luz en la mitad superior
            ft.Container(height=alto * 0.45, top=1, left=6, right=6, border_radius=10,
                         gradient=_degradado(ft.Colors.with_opacity(0.45, BLANCO), ft.Colors.with_opacity(0.0, BLANCO))),
        ]),
        height=alto, border_radius=14, gradient=_degradado(claro, medio, oscuro),
        border=ft.border.all(1, borde), shadow=_sombras(0.7), on_click=al_pulsar, expand=expand,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT), scale=1, on_hover=_relieve_hover)
    cuerpo.data = texto
    return cuerpo


def boton_claro(texto, al_pulsar, icono=None, color=INDIGO):
    return boton(texto, al_pulsar, icono, color="claro", alto=44)


def campo(etiqueta, valor="", **kw):
    """Campo hundido en el papel."""
    opciones = dict(border_radius=12, border_color="#C9C1B0", focused_border_color=TURQUESA, border_width=1.2,
                    label_style=ft.TextStyle(color=INDIGO, weight=ft.FontWeight.W_600), filled=True,
                    fill_color="#F6F2EA", bgcolor="#F6F2EA")
    opciones.update(kw)
    if "bgcolor" in kw:
        opciones["fill_color"] = kw["bgcolor"]
    return ft.TextField(label=etiqueta, value=valor, **opciones)


def chip(texto, color=INDIGO, texto_color=BLANCO, icono=None):
    contenido = [ft.Text(texto, size=12, color=texto_color, weight=ft.FontWeight.BOLD, style=_sombra_texto())]
    if icono:
        contenido.insert(0, ft.Icon(icono, size=14, color=texto_color))
    return ft.Container(ft.Row(contenido, spacing=4, tight=True), border_radius=20,
                        gradient=_degradado(ft.Colors.with_opacity(0.75, color), color),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.6, "#000000")),
                        padding=ft.padding.symmetric(horizontal=11, vertical=5), shadow=_sombras(0.3))


def icono_redondo(icono, color, tam=46):
    """Botón circular de vidrio con un ícono."""
    return ft.Container(ft.Icon(icono, color=BLANCO, size=tam * 0.5), width=tam, height=tam, border_radius=tam,
                        gradient=_degradado(ft.Colors.with_opacity(0.7, color), color),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.5, "#000000")),
                        shadow=_sombras(0.5), alignment=ft.alignment.center)


def mosaico(imagen: str, tam: int = 56):
    return ft.Image(src=imagen, width=tam, height=tam, fit=ft.ImageFit.CONTAIN)


def placa_institucional(compacta=False):
    """Placa metálica con los logos del TecNM y del Instituto Tecnológico de Matehuala."""
    logos = ft.Row([ft.Image(src="logo_tecnm.png", height=34 if compacta else 46, fit=ft.ImageFit.CONTAIN),
                    ft.Container(width=1, height=34 if compacta else 44, bgcolor="#C9C1B0"),
                    ft.Image(src="logo_itmh.png", height=40 if compacta else 54, fit=ft.ImageFit.CONTAIN)],
                   spacing=12, tight=True, alignment=ft.MainAxisAlignment.CENTER,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)
    return ft.Container(logos, gradient=_degradado("#FFFFFF", "#ECE8E0", "#DCD6CA"), border_radius=14,
                        border=ft.border.all(1, "#BDB5A3"), shadow=_sombras(0.6),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8 if compacta else 12))


def barra_progreso(completos: int, total: int, color: str):
    """Barra con volumen: canal hundido y relleno de vidrio."""
    claro = ft.Colors.with_opacity(0.65, color)
    partes = []
    if completos:
        partes.append(ft.Container(expand=completos, border_radius=10, gradient=_degradado(claro, color),
                                   border=ft.border.all(1, ft.Colors.with_opacity(0.5, "#000000"))))
    if total - completos:
        partes.append(ft.Container(expand=total - completos))
    return ft.Container(ft.Row(partes, spacing=0), height=16, border_radius=10, padding=2,
                        gradient=_degradado("#D4CDBE", "#EAE5DA"), border=ft.border.all(1, "#BDB5A3"))


# ======================================================================
#  Aplicación
# ======================================================================
class AppTechMth:
    def __init__(self, page: ft.Page, bot: Bot, *, modo: str = "escritorio", clave_coordinacion: str = "",
                 respaldo=None, dir_assets: Path | None = None):
        self.page = page
        self.bot = bot
        self.modo_ejecucion = modo            # escritorio | servidor | demo
        self.clave = clave_coordinacion
        self.respaldo = respaldo
        self.assets = Path(dir_assets) if dir_assets else None
        self.alumno: dict | None = None
        self.pantalla = "portal"              # portal | app | coordinacion
        self.vista = "inicio"
        self.paso = "numero"                  # numero | datos | confirmar | registrado | listo
        self.num = ""
        self.nuevo = True
        self.existente: dict | None = None
        self.limpios: dict = {}
        self.form: dict[str, str] = {}
        self.historiales: dict[tuple[str, str], list[dict]] = {}
        self.ultima: dict | None = None
        self.panel_abierto = True
        self.ocupado = False
        self.coord_ok = False
        self.ancho = page.width or 1280
        self.modo = _modo(self.ancho)
        self.contacto = {"whatsapp": "", "telegram": "", "llamadas": "", "correo": "", "perfil": "",
                         "proveedor": "gmail", "asunto": "Duda sobre mi titulación", "duracion": "30"}
        self.refs: dict = {}
        self._configurar_pagina()
        self.render()

    # ------------------------------------------------------------------ página
    def _configurar_pagina(self):
        p = self.page
        p.title = "TechMth Solutions · Coordinación de Titulación"
        p.theme_mode = ft.ThemeMode.LIGHT
        p.bgcolor = CREMA
        p.padding = 0
        p.spacing = 0
        p.theme = ft.Theme(color_scheme=ft.ColorScheme(primary=AZUL, on_primary=BLANCO, secondary=TURQUESA,
                                                       on_secondary=BLANCO, surface=BLANCO, on_surface=AZUL,
                                                       primary_container=LAVANDA_CLARO, outline=INDIGO))
        try:
            p.window.min_width, p.window.min_height = 360, 600
            if self.assets and (self.assets / "icon.ico").exists():
                p.window.icon = str((self.assets / "icon.ico").resolve())   # logo de TechMth en la ventana
        except AttributeError:
            pass
        for nombre in ("on_resized", "on_resize"):
            try:
                setattr(p, nombre, self._al_redimensionar)
            except Exception:  # noqa: BLE001
                pass

    def _al_redimensionar(self, e):
        self.ancho = getattr(e, "width", None) or self.page.width or self.ancho
        modo = _modo(self.ancho)
        if modo != self.modo:
            self.modo = modo
            self.render()

    def aviso(self, texto, error=False):
        self.page.open(ft.SnackBar(ft.Text(texto, color=BLANCO), bgcolor=ROJO if error else AZUL,
                                   duration=4000, show_close_icon=True, close_icon_color=BLANCO))

    # ------------------------------------------------------------------ armado
    def render(self):
        p = self.page
        p.controls.clear()
        p.navigation_bar = None
        p.end_drawer = None
        cuerpo = {"portal": self._portal, "app": self._app, "coordinacion": self._coordinacion}[self.pantalla]()
        fondo = ft.Container(ft.Column([self._barra_superior(), cuerpo], spacing=0, expand=True), expand=True,
                             gradient=_degradado("#F7F3EA", "#EDE6D8", "#E6DECD"))   # mesa de papel
        p.add(ft.SafeArea(fondo, expand=True))
        p.update()

    def _barra_superior(self):
        angosta = self.modo == "angosta"
        izquierda = ft.Row([
            ft.Container(ft.Image(src="icon.png", fit=ft.ImageFit.CONTAIN), width=52 if not angosta else 42,
                         height=52 if not angosta else 42, border_radius=14, padding=3,
                         gradient=_degradado("#FFFFFF", "#E9E3D6"), border=ft.border.all(1, "#BDB5A3"),
                         shadow=_sombras(0.6)),
            ft.Column([
                ft.Text("TechMth Solutions", size=21 if not angosta else 17, weight=ft.FontWeight.BOLD, color=BLANCO,
                        style=_sombra_texto()),
                ft.Text("Coordinación de Titulación" + ("" if angosta else " · Atención a egresados"),
                        size=12, color="#C7CCF5", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=0, expand=True),
        ], spacing=12, expand=True)
        derecha = []
        if self.modo == "amplia":
            derecha.append(placa_institucional(compacta=True))
        if self.pantalla == "app" and self.alumno:
            nombre = str(self.alumno.get("nombre") or "").split(" ")[0]
            if self.modo == "amplia":
                derecha.append(chip(f"{nombre} · {self.alumno.get('num_control', '')}", INDIGO, icono=I.PERSON_ROUNDED))
            derecha += [
                ft.Container(icono_redondo(I.ASSIGNMENT_TURNED_IN_ROUNDED, TURQUESA if self.panel_visible() else INDIGO, 40),
                             tooltip="Mi avance", on_click=lambda _: self.alternar_panel()),
                ft.Container(icono_redondo(I.LOGOUT_ROUNDED, "#7A2E2E", 40), tooltip="Salir",
                             on_click=lambda _: self.salir()),
            ]
        elif self.pantalla == "coordinacion":
            derecha.append(ft.Container(icono_redondo(I.ARROW_BACK_ROUNDED, INDIGO, 40), tooltip="Volver al portal",
                                        on_click=lambda _: self.salir()))
        return ft.Column([
            ft.Container(height=1, bgcolor=ft.Colors.with_opacity(0.25, BLANCO)),        # filo de luz
            ft.Container(ft.Row([izquierda, *derecha], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                         gradient=_degradado(*PIEL), padding=ft.padding.symmetric(horizontal=16, vertical=10),
                         border=ft.border.only(bottom=ft.BorderSide(1, "#000000")),
                         shadow=[ft.BoxShadow(blur_radius=10, offset=ft.Offset(0, 4),
                                              color=ft.Colors.with_opacity(0.35, "#000000"))]),
            ft.Container(height=3, gradient=_degradado(TURQUESA, "#1C7C8D")),
        ], spacing=0)

    # ==================================================================
    #  Portal de egresados
    # ==================================================================
    def _portal(self):
        angosta = self.modo == "angosta"
        ancho_tarjeta = min(560 if self.paso != "confirmar" else 980, self.ancho - (32 if angosta else 0)
                            - (0 if angosta else self.ancho * 0.4))
        tarjeta_form = tarjeta(ft.Column(self._contenido_paso(ancho_tarjeta), spacing=16, tight=True),
                               padding=26 if not angosta else 18, width=max(300, ancho_tarjeta))
        pie = ft.TextButton("Acceso Coordinación", icon=I.ADMIN_PANEL_SETTINGS_OUTLINED,
                            on_click=lambda _: self._ir_coordinacion(), style=ft.ButtonStyle(color=INDIGO))
        formulario = ft.Container(
            ft.Column([tarjeta_form, pie] + ([placa_institucional()] if angosta else []),
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
                      scroll=None if angosta else ft.ScrollMode.AUTO, expand=not angosta),
            padding=ft.padding.symmetric(horizontal=16 if angosta else 32, vertical=24),
            alignment=ft.alignment.top_center, expand=not angosta)
        marca = self._marca(angosta)
        if angosta:
            return ft.Column([marca, formulario], scroll=ft.ScrollMode.AUTO, expand=True, spacing=0)
        return ft.Row([ft.Container(marca, expand=2), ft.Container(formulario, expand=3)], expand=True, spacing=0,
                      vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def _logo_en_papel(self, ancho):
        return ft.Container(ft.Image(src="logo_techmth.png", width=ancho, fit=ft.ImageFit.CONTAIN),
                            gradient=_degradado("#FFFDF8", "#F1EBDD"), border_radius=22,
                            border=ft.border.all(1, "#CFC6B2"), padding=ft.padding.symmetric(horizontal=18, vertical=10),
                            shadow=_sombras(1.4))

    def _marca(self, angosta: bool):
        if angosta:
            return ft.Container(ft.Column([self._logo_en_papel(210),
                                           ft.Text("Portal de egresados", size=22, weight=ft.FontWeight.BOLD, color=BLANCO,
                                                   style=_sombra_texto())],
                                          horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                                gradient=_degradado(*PIEL), padding=20, alignment=ft.alignment.center)
        ventajas = [(I.TASK_ALT_ROUNDED, "Consulta lo que ya tienes y lo que te falta"),
                    (I.QUESTION_ANSWER_ROUNDED, "Resuelve tus dudas del proceso de titulación"),
                    (I.FORUM_ROUNDED, "Atención por WhatsApp, Telegram, correo y llamadas")]
        return ft.Container(
            ft.Column([
                placa_institucional(),
                ft.Container(height=10),
                self._logo_en_papel(330),
                ft.Text("Conectamos procesos, simplificamos trámites escolares", size=13, italic=True,
                        color=ft.Colors.with_opacity(0.85, BLANCO), text_align=ft.TextAlign.CENTER),
                ft.Container(height=8),
                ft.Text("Portal de egresados", size=32, weight=ft.FontWeight.BOLD, color=BLANCO, style=_sombra_texto()),
                ft.Text("Titulación integral por residencia profesional", size=15, color="#C7CCF5"),
                ft.Container(height=4, width=140, border_radius=4, margin=ft.margin.symmetric(vertical=12),
                             gradient=_degradado("#6FD0DE", TURQUESA)),
                *[ft.Row([icono_redondo(ic, TURQUESA, 40), ft.Text(t, size=14, color=BLANCO, expand=True)], spacing=12)
                  for ic, t in ventajas],
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, scroll=ft.ScrollMode.AUTO),
            gradient=_degradado(*PIEL), padding=34, alignment=ft.alignment.center,
            border=ft.border.only(right=ft.BorderSide(1, "#000000")))

    def _pasos(self, actual: int):
        celdas = []
        for n, texto in enumerate(("Número de control", "Tus datos", "Confirmar"), start=1):
            hecho, activo = n < actual, n == actual
            color = TURQUESA if hecho else (AZUL if activo else "#9AA0C8")
            celdas.append(ft.Column([
                ft.Container(ft.Icon(I.CHECK, color=BLANCO, size=16) if hecho else
                             ft.Text(str(n), color=BLANCO, weight=ft.FontWeight.BOLD, style=_sombra_texto()),
                             width=34, height=34, border_radius=34, alignment=ft.alignment.center,
                             gradient=_degradado(ft.Colors.with_opacity(0.7, color), color),
                             border=ft.border.all(1, ft.Colors.with_opacity(0.5, "#000000")), shadow=_sombras(0.4)),
                ft.Text(texto, size=11, color=AZUL if activo else SUAVE,
                        weight=ft.FontWeight.BOLD if activo else ft.FontWeight.NORMAL, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, expand=True))
            if n < 3:
                celdas.append(ft.Container(height=4, expand=True, border_radius=4, margin=ft.margin.only(bottom=18),
                                           gradient=_degradado("#6FD0DE", TURQUESA) if hecho else
                                           _degradado("#D4CDBE", "#EAE5DA")))
        return ft.Row(celdas, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

    def _titulo(self, texto, sub=""):
        filas = [ft.Text(texto, size=24, weight=ft.FontWeight.BOLD, color=AZUL, style=_sombra_texto(True))]
        if sub:
            filas.append(ft.Text(sub, size=13, color=SUAVE))
        return ft.Column(filas, spacing=4)

    def _contenido_paso(self, ancho: float):
        return {"numero": self._paso_numero, "datos": self._paso_datos, "confirmar": lambda: self._paso_confirmar(ancho),
                "registrado": self._paso_registrado, "listo": self._paso_listo}[self.paso]()

    # paso 1 -----------------------------------------------------------
    def _paso_numero(self):
        entrada = campo("", self.num, hint_text="24660999", text_size=24, text_align=ft.TextAlign.CENTER,
                        border_radius=14, autofocus=True, max_length=9, keyboard_type=ft.KeyboardType.NUMBER,
                        prefix_icon=I.BADGE_OUTLINED, helper_text="8 dígitos, por ejemplo 24660999")
        entrada.label = "Número de control"
        self.refs["num"] = entrada

        def continuar(_=None):
            num = registro.leer_num_control(entrada.value or "")
            if not num:
                entrada.error_text = "Revisa tu número: deben ser 8 dígitos."
                self.page.update()
                return
            self.num = num
            self.existente = registro.buscar(self.bot.excel, num)
            if self.existente:
                self.paso = "registrado"
            else:
                self.nuevo = True
                self.form = {c: "" for c, _ in registro.CAMPOS}
                self.form["correo_institucional"] = registro.correo_sugerido(num)
                self.paso = "datos"
            self.render()

        entrada.on_submit = continuar
        return [self._pasos(1),
                self._titulo("¡Bienvenida(o)!", "Ingresa tu número de control para consultar tu proceso de titulación."),
                entrada, ft.Row([boton("Continuar", continuar, I.ARROW_FORWARD_ROUNDED, expand=True)])]

    # ya registrado ------------------------------------------------------
    def _paso_registrado(self):
        nombre = str(self.existente.get("nombre") or "").split(" ")[0]

        def actualizar(_):
            self.nuevo = False
            self.form = {c: "" for c, _ in registro.CAMPOS}
            self.paso = "datos"
            self.render()

        def otro(_):
            self.num, self.paso = "", "numero"
            self.render()

        return [ft.Row([icono_redondo(I.WAVING_HAND_ROUNDED, TURQUESA, 68)], alignment=ft.MainAxisAlignment.CENTER),
                self._titulo(f"¡Hola de nuevo{', ' + nombre if nombre else ''}!",
                             f"El número de control {self.num} ya tiene sus datos registrados."),
                ft.Row([boton("Entrar", lambda _: self.entrar(self.existente), I.LOGIN_ROUNDED, expand=True)]),
                ft.Row([boton_claro("Actualizar mis datos", actualizar, I.EDIT_ROUNDED)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([ft.TextButton("No soy yo · usar otro número", on_click=otro)], alignment=ft.MainAxisAlignment.CENTER)]

    # paso 2 -------------------------------------------------------------
    def _paso_datos(self):
        controles = {}
        ayudas = {"correo_personal": "Opcional", "telefono": "10 dígitos, por ejemplo 488 000 1234",
                  "correo_institucional": "Tu correo del Tec"}
        iconos = {"num_control": I.BADGE_OUTLINED, "nombre": I.PERSON_OUTLINE, "correo_institucional": I.SCHOOL_OUTLINED,
                  "correo_personal": I.ALTERNATE_EMAIL, "telefono": I.PHONE_ANDROID}
        for clave, etiqueta in registro.CAMPOS:
            ayuda = ayudas.get(clave) if self.nuevo else "Vacío = conservar el dato actual"
            if clave == "carrera":
                c = ft.Dropdown(label=etiqueta, value=self.form.get("carrera") or None, border_radius=12,
                                border_color="#C9C1B0", focused_border_color=TURQUESA, filled=True, fill_color="#F6F2EA",
                                label_style=ft.TextStyle(color=INDIGO, weight=ft.FontWeight.W_600),
                                leading_icon=I.WORKSPACE_PREMIUM_OUTLINED,
                                helper_text=None if self.nuevo else ayuda, expand=True,
                                options=[ft.dropdown.Option(key=k, text=f"{k} · {v}") for k, v in registro.CARRERAS.items()])
            elif clave == "num_control":
                c = campo(etiqueta, self.num, read_only=True, prefix_icon=iconos[clave], bgcolor=LAVANDA_CLARO,
                          text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=AZUL))
            else:
                c = campo(etiqueta, self.form.get(clave, ""), prefix_icon=iconos.get(clave), helper_text=ayuda,
                          keyboard_type=ft.KeyboardType.PHONE if clave == "telefono" else
                          ft.KeyboardType.EMAIL if "correo" in clave else ft.KeyboardType.TEXT,
                          capitalization=ft.TextCapitalization.WORDS if clave == "nombre" else None)
            controles[clave] = c

        def revisar(_=None):
            self.form = {k: (c.value or "") for k, c in controles.items()}
            limpios, errores = registro.validar(self.form, self.nuevo)
            for k, c in controles.items():
                c.error_text = errores.get(k)
            if not self.nuevo and not limpios and not errores:
                controles["nombre"].error_text = "No escribiste ningún cambio."
                errores = {"nombre": "x"}
            if errores:
                self.page.update()
                return
            self.limpios = limpios
            self.paso = "confirmar"
            self.render()

        def regresar(_):
            self.paso = "numero" if self.nuevo else "registrado"
            self.render()

        titulo = (self._titulo("Completa tus datos", "Se guardan en el mismo orden que la tabla de la Coordinación.")
                  if self.nuevo else
                  self._titulo("Actualiza tus datos", "Escribe solo lo que quieras cambiar."))
        return [self._pasos(2), titulo, *controles.values(),
                ft.Row([boton_claro("Regresar", regresar, I.ARROW_BACK_ROUNDED),
                        boton("Revisar mis datos", revisar, I.ARROW_FORWARD_ROUNDED)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True, run_spacing=10)]

    # paso 3 -------------------------------------------------------------
    def _valores(self) -> list[str]:
        if self.nuevo:
            return registro.fila_para_mostrar(self.num, self.limpios)
        actual = {**{k: ("" if v is None else str(v)) for k, v in (self.existente or {}).items()}, **self.limpios}
        return [self.num] + [actual.get(c, "") for c, _ in registro.CAMPOS[1:]]

    def _paso_confirmar(self, ancho: float):
        valores = self._valores()
        cambios = set(self.limpios) if not self.nuevo else set()
        if ancho >= 760:   # igual que la tabla de Excel: encabezados arriba
            tabla = ft.Container(ft.DataTable(
                columns=[ft.DataColumn(ft.Text(e, color=BLANCO, weight=ft.FontWeight.BOLD, size=12, style=_sombra_texto()))
                         for _, e in registro.CAMPOS],
                rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(v or "—", size=12, color=AZUL,
                                                            weight=ft.FontWeight.BOLD if c in cambios else None))
                                        for (c, _), v in zip(registro.CAMPOS, valores)],
                                 color=TURQUESA_CLARO)],
                heading_row_color=TABLA_ENC, heading_row_height=44, data_row_min_height=48, column_spacing=18,
                horizontal_lines=ft.BorderSide(1, BORDE)), border_radius=12, border=ft.border.all(1, "#BDB5A3"),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS, shadow=_sombras(0.6))
            tabla = ft.Row([tabla], scroll=ft.ScrollMode.AUTO)
        else:              # pantallas chicas: encabezado a la izquierda
            tabla = ft.Column([
                ft.Row([ft.Container(ft.Text(e, color=BLANCO, weight=ft.FontWeight.BOLD, size=12), bgcolor=TABLA_ENC,
                                     padding=10, width=130),
                        ft.Container(ft.Text(v or "—", size=12, color=AZUL,
                                             weight=ft.FontWeight.BOLD if c in cambios else None),
                                     bgcolor=TURQUESA_CLARO if c in cambios else BLANCO, padding=10, expand=True,
                                     border=ft.border.all(1, BORDE))], spacing=0)
                for (c, e), v in zip(registro.CAMPOS, valores)], spacing=2)

        def guardar(_):
            try:
                ok = registro.guardar(self.bot.excel, self.num, self.limpios, self.nuevo)
            except Exception as ex:  # noqa: BLE001
                self.aviso(f"No se pudo guardar: {ex}", error=True)
                return
            self.existente = {"num_control": self.num, **(self.existente or {}), **self.limpios}
            self.refs["guardado_ok"] = ok
            self.paso = "listo"
            self.render()

        def corregir(_):
            self.paso = "datos"
            self.render()

        return [self._pasos(3),
                self._titulo("Confirma tus datos", "Así quedarán guardados en la tabla de egresados."), tabla,
                ft.Row([boton_claro("Corregir", corregir, I.EDIT_ROUNDED),
                        boton("Guardar y entrar", guardar, I.CHECK_ROUNDED, color="verde")],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True, run_spacing=10)]

    def _paso_listo(self):
        nombre = str(self.existente.get("nombre") or "").split(" ")[0]
        ok = self.refs.get("guardado_ok", True)
        return [ft.Row([icono_redondo(I.CHECK_ROUNDED, VERDE, 76)], alignment=ft.MainAxisAlignment.CENTER),
                self._titulo(f"¡Listo, {nombre}!", "Tus datos quedaron guardados." if ok else
                             "Tus datos se guardarán en cuanto el archivo de Excel esté disponible."),
                ft.Row([boton("Entrar", lambda _: self.entrar(self.existente), I.LOGIN_ROUNDED, expand=True)])]

    # ==================================================================
    #  Sesión
    # ==================================================================
    def entrar(self, alumno: dict):
        self.alumno = {k: ("" if v is None else v) for k, v in alumno.items() if not str(k).startswith("_")}
        a = self.alumno
        tel = str(a.get("telefono") or "")
        self.contacto.update({"whatsapp": tel, "telegram": tel, "llamadas": tel,
                              "correo": str(a.get("correo_personal") or a.get("correo_institucional") or ""),
                              "perfil": str(a.get("nombre") or "").split(" ")[0]})
        self.historiales.clear()
        self.bot.sesiones.clear()
        self.ultima = None
        self.pantalla, self.vista = "app", "inicio"
        self.panel_abierto = self.modo == "amplia"
        self.render()

    def salir(self):
        self.alumno = None
        self.historiales.clear()
        self.bot.sesiones.clear()
        self.pantalla, self.paso, self.num, self.coord_ok = "portal", "numero", "", False
        self.render()

    # ==================================================================
    #  Aplicación del egresado
    # ==================================================================
    def panel_visible(self) -> bool:
        return self.modo == "amplia" and self.panel_abierto

    def alternar_panel(self):
        if self.modo == "amplia":
            self.panel_abierto = not self.panel_abierto
            self.render()
        else:
            self._abrir_cajon()

    def _abrir_cajon(self):
        cajon = ft.NavigationDrawer(position=ft.NavigationDrawerPosition.END, bgcolor="#F7F3EA",
                                    controls=[ft.Container(ft.Column(self._contenido_panel(), spacing=12),
                                                           padding=16, width=min(ANCHO_PANEL, self.ancho - 40))])
        self.refs["cajon"] = cajon
        self.page.open(cajon)

    def _boton_dock(self, clave, imagen, nombre, tam):
        activo = clave == self.vista
        return ft.Container(
            mosaico(imagen, tam), tooltip=nombre, padding=5, border_radius=20,
            gradient=_degradado("#D9DCF7", "#B9BEEA") if activo else None,
            border=ft.border.all(2, TURQUESA) if activo else ft.border.all(2, ft.Colors.TRANSPARENT),
            shadow=[ft.BoxShadow(blur_radius=12, color=ft.Colors.with_opacity(0.55, TURQUESA))] if activo else None,
            on_click=lambda _: self.ir_a(clave), animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=1, on_hover=_relieve_hover)

    def _app(self):
        contenido = ft.Container(self._vista_actual(), expand=True,
                                 padding=ft.padding.symmetric(horizontal=12 if self.modo == "angosta" else 24, vertical=16))
        if self.modo == "angosta":   # celular: barra inferior solo con íconos
            barra = ft.Container(
                ft.Row([self._boton_dock(c, img, n, 44) for c, img, n in VISTAS],
                       alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                gradient=_degradado("#FDFBF7", "#E6DFD2"), padding=ft.padding.symmetric(vertical=6),
                border=ft.border.only(top=ft.BorderSide(1, "#BDB5A3")),
                shadow=[ft.BoxShadow(blur_radius=10, offset=ft.Offset(0, -3), color=ft.Colors.with_opacity(0.18, "#000000"))])
            return ft.Column([contenido, barra], spacing=0, expand=True)
        dock = ft.Container(
            ft.Column([self._boton_dock(c, img, n, 54 if self.modo == "amplia" else 46) for c, img, n in VISTAS],
                      spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
            width=96 if self.modo == "amplia" else 84, padding=ft.padding.symmetric(vertical=18),
            gradient=_degradado("#FDFBF7", "#ECE6DA", "#E2DACB"),
            border=ft.border.only(right=ft.BorderSide(1, "#BDB5A3")),
            shadow=[ft.BoxShadow(blur_radius=10, offset=ft.Offset(3, 0), color=ft.Colors.with_opacity(0.15, "#000000"))])
        fila = [dock, contenido]
        if self.panel_visible():
            fila.append(ft.Container(ft.Column(self._contenido_panel(), spacing=12, scroll=ft.ScrollMode.AUTO),
                                     width=ANCHO_PANEL, padding=18, gradient=_degradado("#FFFFFF", "#F1ECE2"),
                                     border=ft.border.only(left=ft.BorderSide(1, "#BDB5A3")),
                                     shadow=[ft.BoxShadow(blur_radius=12, offset=ft.Offset(-3, 0),
                                                          color=ft.Colors.with_opacity(0.15, "#000000"))]))
        return ft.Row(fila, expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def ir_a(self, vista: str):
        self.vista = vista
        self.render()

    def _vista_actual(self):
        return {"inicio": self._inicio, "whatsapp": lambda: self._chat("whatsapp"),
                "telegram": lambda: self._chat("telegram"), "correo": self._correo,
                "llamadas": self._llamadas}[self.vista]()

    # ------------------------------------------------------------- Mi avance
    def _mi_avance(self, compacto=False):
        num = str((self.alumno or {}).get("num_control") or "")
        try:
            av = avance.calcular(self.bot.excel, num)
        except Exception as ex:  # noqa: BLE001
            return ft.Text(f"No se pudo consultar tu avance: {ex}", color=ROJO)
        color = VERDE if av["listo"] else TURQUESA
        titulo = ft.Row([
            ft.Text("Mi avance de titulación", size=15 if compacto else 20, weight=ft.FontWeight.BOLD, color=AZUL,
                    expand=True, style=_sombra_texto(True)),
            chip(f"{av['completos']} de {av['total']}", color),
        ])

        def lista(items, icono, color_icono):
            return [ft.Row([ft.Icon(icono, size=16, color=color_icono), ft.Text(t, size=13, color=AZUL, expand=True)],
                           spacing=8, vertical_alignment=ft.CrossAxisAlignment.START) for t in items]

        falta = lista(av["falta"], I.SCHEDULE_ROUNDED, "#B26A00") + lista(
            [f"{x} (sin registro de la Coordinación)" for x in av["sin_registro"]], I.HELP_OUTLINE, SUAVE)
        caja_tiene = ft.Container(ft.Column([
            ft.Row([ft.Icon(I.CHECK_CIRCLE_ROUNDED, color=VERDE),
                    ft.Text("Lo que ya tienes", weight=ft.FontWeight.BOLD, color=VERDE)]),
            *(lista(av["tiene"], I.CHECK_ROUNDED, VERDE) or [ft.Text("Aún no hay requisitos registrados.", size=13, color=SUAVE)]),
        ], spacing=6), gradient=_degradado("#F3FBF6", "#DFF2E6"), border=ft.border.all(1, "#B7DEC5"), border_radius=14,
            padding=14, shadow=_sombras(0.4), col={"xs": 12, "md": 12 if compacto else 6})
        caja_falta = ft.Container(ft.Column([
            ft.Row([ft.Icon(I.PENDING_ACTIONS_ROUNDED, color="#B26A00"),
                    ft.Text("Lo que te falta", weight=ft.FontWeight.BOLD, color="#B26A00")]),
            *(falta or [ft.Text("¡Nada! Todo está completo.", size=13, color=VERDE)]),
        ], spacing=6), gradient=_degradado("#FFF9F0", "#FCE9CF"), border=ft.border.all(1, "#EBCB98"), border_radius=14,
            padding=14, shadow=_sombras(0.4), col={"xs": 12, "md": 12 if compacto else 6})
        filas_pasos = []
        for n, (paso, detalle, hecho) in enumerate(av["pasos"], start=1):
            numero = ft.Container(
                ft.Icon(I.CHECK_ROUNDED, size=16, color=BLANCO) if hecho else
                ft.Text(str(n), size=13, weight=ft.FontWeight.BOLD, color=BLANCO, style=_sombra_texto()),
                width=30, height=30, border_radius=30, alignment=ft.alignment.center,
                gradient=_degradado("#6BD99A", VERDE) if hecho else _degradado("#7E88D6", INDIGO),
                border=ft.border.all(1, ft.Colors.with_opacity(0.5, "#000000")), shadow=_sombras(0.3),
                tooltip="Ya lo cumpliste" if hecho else None)
            filas_pasos.append(ft.Row([
                numero,
                ft.Column([ft.Text(paso, size=14 if compacto else 15, weight=ft.FontWeight.BOLD,
                                   color=VERDE if hecho else AZUL),
                           ft.Text(detalle, size=12 if compacto else 13, color=SUAVE)], spacing=3, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START))
        siguiente = ft.Container(ft.Column([
            ft.Row([icono_redondo(I.ROUTE_ROUNDED, INDIGO, 38),
                    ft.Column([ft.Text("Ruta para concluir tu titulación", size=15 if compacto else 16,
                                       weight=ft.FontWeight.BOLD, color=AZUL, style=_sombra_texto(True)),
                               ft.Text("Sigue estos pasos en orden para poder titularte.", size=12, color=SUAVE)],
                              spacing=1, expand=True)], spacing=12),
            ft.Divider(height=14, color="#BCC2EC"),
            ft.Column(filas_pasos, spacing=14),
        ], spacing=4), gradient=_degradado("#F7F8FE", "#DDE0F8"), border=ft.border.all(1, "#BCC2EC"),
            border_radius=14, padding=16, shadow=_sombras(0.4))
        return ft.Column([titulo, barra_progreso(av["completos"], av["total"], color),
                          ft.ResponsiveRow([caja_tiene, caja_falta], spacing=12, run_spacing=12), siguiente], spacing=12)

    def _contenido_panel(self):
        controles = [
            ft.Row([icono_redondo(I.ASSIGNMENT_TURNED_IN_ROUNDED, INDIGO, 42),
                    ft.Column([ft.Text("Mi avance", size=17, weight=ft.FontWeight.BOLD, color=AZUL, style=_sombra_texto(True)),
                               ft.Text("Coordinación de Titulación", size=11, color=SUAVE)], spacing=0, expand=True),
                    ft.IconButton(I.CLOSE_ROUNDED, icon_color=INDIGO, tooltip="Cerrar",
                                  on_click=lambda _: self._cerrar_panel())]),
            self._mi_avance(compacto=True),
        ]
        if self.ultima:
            u = self.ultima
            controles += [ft.Divider(color=BORDE), ft.Text("TU ÚLTIMA CONSULTA", size=11, weight=ft.FontWeight.BOLD, color=INDIGO),
                          tarjeta(ft.Column([
                              ft.Text(f"{u['hora']} · {u['canal']} · {TEMAS.get(u['intencion'], u['intencion'])}",
                                      size=12, weight=ft.FontWeight.BOLD, color=AZUL),
                              ft.Text("Turnada a la Coordinación: te contactarán." if u["pendiente"] else "Respondida ✓",
                                      size=12, color=ROJO if u["pendiente"] else VERDE)], spacing=2), padding=12)]
        controles += [ft.Divider(color=BORDE), ft.Text("PREGUNTAS FRECUENTES", size=11, weight=ft.FontWeight.BOLD, color=INDIGO),
                      ft.Row([self._chip_pregunta(e, t) for e, t in SUGERIDAS], wrap=True, spacing=6, run_spacing=8)]
        return controles

    def _cerrar_panel(self):
        if self.modo == "amplia":
            self.panel_abierto = False
            self.render()
        elif self.refs.get("cajon") is not None:
            self.page.close(self.refs.pop("cajon"))

    def _chip_pregunta(self, etiqueta, texto):
        """Pastilla de vidrio que se puede pulsar."""
        return ft.Container(ft.Text(etiqueta, size=12, color=AZUL, weight=ft.FontWeight.BOLD, style=_sombra_texto(True)),
                            gradient=_degradado("#FFFFFF", "#E3E6FA"), border=ft.border.all(1, "#B9BEEA"),
                            border_radius=20, padding=ft.padding.symmetric(horizontal=13, vertical=8),
                            shadow=_sombras(0.35), on_click=lambda _: self._pregunta(texto),
                            animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT), scale=1, on_hover=_relieve_hover)

    def _pregunta(self, texto):
        if self.modo != "amplia":
            self._cerrar_panel()
        if self.vista not in ("whatsapp", "telegram", "correo", "llamadas"):
            self.vista = "whatsapp"
            self.render()
        self.enviar(self.vista, texto)

    # ------------------------------------------------------------- Inicio
    def _inicio(self):
        nombre = str((self.alumno or {}).get("nombre") or "").split(" ")[0]
        angosta = self.modo == "angosta"
        heroe = ft.Container(
            ft.ResponsiveRow([
                ft.Container(self._logo_en_papel(290 if not angosta else 210), col={"xs": 12, "md": 5},
                             alignment=ft.alignment.center),
                ft.Column([
                    ft.Text(f"¡Hola, {nombre}!", size=30 if not angosta else 22, weight=ft.FontWeight.BOLD, color=BLANCO,
                            style=_sombra_texto()),
                    ft.Text("Bienvenida(o) a la Coordinación de Titulación", size=16, color="#C7CCF5"),
                    ft.Text("Aquí resuelves tus dudas sobre tu proceso de titulación y consultas lo que ya tienes y lo "
                            "que te falta para titularte.", size=13, color=BLANCO),
                ], spacing=6, col={"xs": 12, "md": 7}, alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=20, run_spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            gradient=_degradado(*PIEL), border_radius=22, padding=24 if not angosta else 18,
            border=ft.border.all(1, "#000000"), shadow=_sombras(1.3))
        canales = []
        for clave, imagen, nombre_c, desc, _ in CANALES_UI:
            canales.append(ft.Container(
                ft.Column([mosaico(imagen, 72), ft.Text(nombre_c, size=15, weight=ft.FontWeight.BOLD, color=AZUL,
                                                        style=_sombra_texto(True)),
                           ft.Text(desc, size=12, color=SUAVE, text_align=ft.TextAlign.CENTER)],
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                gradient=_degradado(*PAPEL), border_radius=18, padding=18, border=ft.border.all(1, BORDE),
                shadow=_sombras(0.8), col={"xs": 6, "md": 3}, on_click=lambda _, c=clave: self.ir_a(c),
                animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT), scale=1, on_hover=_relieve_hover))
        return ft.Column([
            heroe,
            tarjeta(self._mi_avance(), padding=22, borde="#A9D8E0"),
            ft.Text("CANALES DE ATENCIÓN", size=12, weight=ft.FontWeight.BOLD, color=INDIGO),
            ft.ResponsiveRow(canales, spacing=14, run_spacing=14),
            ft.Container(placa_institucional(), alignment=ft.alignment.center, padding=ft.padding.only(top=8, bottom=8)),
        ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    # ------------------------------------------------------------- mensajes
    def _clave(self, vista: str) -> tuple[str, str]:
        canal = {"llamadas": "llamada", "correo": self.contacto["proveedor"]}.get(vista, vista)
        return canal, self.contacto[vista].strip().lower()

    def enviar(self, vista: str, texto: str):
        if self.ocupado:
            return
        remitente = self.contacto[vista].strip()
        if not remitente:
            self.aviso("Escribe primero tu " + ("correo." if vista == "correo" else "teléfono."), error=True)
            return
        if not texto and vista != "llamadas":
            return
        canal, clave = self._clave(vista)
        dur = int(self.contacto["duracion"]) if self.contacto["duracion"].isdigit() else 0
        msg = MensajeEntrante(canal, remitente, texto, asunto=self.contacto["asunto"] if vista == "correo" else "",
                              nombre_mostrado=self.contacto["perfil"], duracion=dur)
        hora = datetime.now().strftime("%H:%M")
        hist = self.historiales.setdefault((canal, clave), [])
        hist.append({"tipo": "egresado", "texto": texto, "hora": hora, "de": remitente, "asunto": msg.asunto, "seg": dur})
        self.ocupado = True
        self._pintar_mensajes(vista, escribiendo=True)
        inicio = time.time()
        try:
            r = self.bot.procesar(msg)
        except Exception as ex:  # noqa: BLE001
            hist.append({"tipo": "error", "texto": f"Ocurrió un error: {ex}", "hora": hora})
            self.ocupado = False
            self._pintar_mensajes(vista)
            return
        if not EN_NAVEGADOR:
            time.sleep(max(0.0, 0.6 - (time.time() - inicio)))   # pausa natural
        pendiente = r.atendido_por == "Pendiente"
        hist.append({"tipo": "respuesta", "texto": r.texto, "asunto": r.asunto, "hora": datetime.now().strftime("%H:%M"),
                     "via": CANALES[r.canal], "para": r.para, "intencion": r.intencion, "pendiente": pendiente})
        self.ultima = {"hora": hora, "canal": CANALES[canal], "intencion": r.intencion, "pendiente": pendiente}
        self.ocupado = False
        if self.modo == "amplia":
            self.panel_abierto = True
            self.render()
        else:
            self._pintar_mensajes(vista)
            if pendiente or r.intencion == "estatus":
                self._abrir_cajon()

    def _burbuja(self, m: dict, vista: str):
        propio = m["tipo"] == "egresado"
        if m["tipo"] == "error":
            return ft.Text(m["texto"], color=ROJO, weight=ft.FontWeight.BOLD)
        if vista == "correo":
            encabezado = _degradado("#F1F2FD", "#DCE0F8") if propio else _degradado("#ECF8FA", "#CFEDF2")
            return ft.Container(ft.Column([
                ft.Container(ft.Column([
                    ft.Text(f"De: {m['de'] if propio else 'Coordinación de Titulación'}", size=12, weight=ft.FontWeight.BOLD, color=AZUL),
                    ft.Text(f"Para: {'Coordinación de Titulación' if propio else m['para']} · {m['hora']}", size=11, color=SUAVE),
                    ft.Text(f"Asunto: {m['asunto'] or '(sin asunto)'}", size=12, weight=ft.FontWeight.BOLD, color=INDIGO),
                ], spacing=1), gradient=encabezado, padding=12,
                    border=ft.border.only(bottom=ft.BorderSide(1, "#C9C1B0")),
                    border_radius=ft.border_radius.only(top_left=14, top_right=14)),
                ft.Container(ft.Text(m["texto"], size=13, color=AZUL, selectable=True), padding=14),
                *([ft.Container(chip("Turnado a la Coordinación", ROJO, icono=I.FLAG_ROUNDED),
                                padding=ft.padding.only(left=12, bottom=10))] if m.get("pendiente") else []),
            ], spacing=0), gradient=_degradado(*PAPEL), border_radius=14,
                border=ft.border.all(1, "#BCC2EC" if propio else "#A9D8E0"), shadow=_sombras(0.6))
        if vista == "llamadas" and propio:
            dijo = f"«{m['texto']}»" if m["texto"] else "Colgó sin dejar mensaje"
            contenido = ft.Column([ft.Row([icono_redondo(I.PHONE_CALLBACK_ROUNDED, VERDE, 30),
                                           ft.Text(f"Llamada de {m['de']} · {m['seg']} s · {m['hora']}", size=12,
                                                   weight=ft.FontWeight.BOLD, color=AZUL)]),
                                   ft.Text(dijo, size=13, italic=True, color=INDIGO)], spacing=6)
            caja = ft.Container(contenido, gradient=_degradado("#ECF8FA", "#CFEDF2"), border_radius=16, padding=12,
                                border=ft.border.all(1, "#A9D8E0"), shadow=_sombras(0.5), col={"xs": 11, "md": 9})
            return ft.ResponsiveRow([caja], alignment=ft.MainAxisAlignment.END)
        texto = m["texto"].replace("*", "")
        if propio:   # globo de vidrio índigo
            caja = ft.Container(ft.Column([ft.Text(texto, size=14, color=BLANCO, selectable=True, style=_sombra_texto()),
                                           ft.Text(f"{m['hora']}  ✓✓", size=10, color="#D7DBFA", text_align=ft.TextAlign.RIGHT)],
                                          spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
                                gradient=_degradado("#7E88D6", "#4D56A8", "#3B4396"), padding=12,
                                border=ft.border.all(1, "#2E3580"), shadow=_sombras(0.5),
                                col={"xs": 11, "sm": 10, "md": 8, "xl": 7},
                                border_radius=ft.border_radius.only(top_left=18, top_right=18, bottom_left=18, bottom_right=4))
            return ft.ResponsiveRow([caja], alignment=ft.MainAxisAlignment.END)
        detalle = m["hora"] + (f" · enviado por {m['via']}" if vista == "llamadas" else "")
        caja = ft.Container(ft.Column([
            ft.Row([ft.Icon(I.VERIFIED_ROUNDED, size=14, color=TURQUESA),
                    ft.Text("Coordinación de Titulación", size=11, weight=ft.FontWeight.BOLD, color=TURQUESA)], spacing=4),
            ft.Text(texto, size=14, color=AZUL, selectable=True),
            *([chip("Turnado a la Coordinación", ROJO, icono=I.FLAG_ROUNDED)] if m.get("pendiente") else []),
            ft.Text(detalle, size=10, color=SUAVE),
        ], spacing=6), gradient=_degradado("#FFFFFF", "#EEF2F4"), padding=12, col={"xs": 11, "sm": 10, "md": 8, "xl": 7},
            border=ft.border.all(1, ROJO if m.get("pendiente") else "#C5CED4"), shadow=_sombras(0.5),
            border_radius=ft.border_radius.only(top_left=18, top_right=18, bottom_left=4, bottom_right=18))
        return ft.ResponsiveRow([caja], alignment=ft.MainAxisAlignment.START)

    def _bienvenida(self, texto):
        return ft.Container(ft.Column([icono_redondo(I.SUPPORT_AGENT_ROUNDED, TURQUESA, 66),
                                       ft.Text("Coordinación de Titulación", size=16, weight=ft.FontWeight.BOLD, color=AZUL,
                                               style=_sombra_texto(True)),
                                       ft.Text(texto, size=13, color=SUAVE, text_align=ft.TextAlign.CENTER)],
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                            padding=30, alignment=ft.alignment.center)

    def _hist_vista(self, vista):
        canal, clave = self._clave(vista)
        if vista == "llamadas":
            return [m for (c, _), h in self.historiales.items() if c == "llamada" for m in h]
        return self.historiales.get((canal, clave), [])

    def _pintar_mensajes(self, vista: str, escribiendo: bool = False):
        lista: ft.ListView | None = self.refs.get(f"lista_{vista}")
        if lista is None:
            return
        hist = self._hist_vista(vista)
        lista.controls = [self._burbuja(m, vista) for m in hist] or [self._bienvenida(self.refs.get(f"bienvenida_{vista}", ""))]
        if escribiendo:
            lista.controls.append(ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=TURQUESA),
                                          ft.Text("Escribiendo respuesta…", size=12, italic=True, color=SUAVE)]))
        self.page.update()

    def _pintar_diferido(self, vista):
        hist = self._hist_vista(vista)
        lista = self.refs[f"lista_{vista}"]
        lista.controls = [self._burbuja(m, vista) for m in hist] or [self._bienvenida(self.refs[f"bienvenida_{vista}"])]

    def _encabezado_canal(self, vista, titulo, sub):
        imagen = next(img for c, img, _ in VISTAS if c == vista)
        return tarjeta(ft.Row([mosaico(imagen, 60),
                               ft.Column([ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, color=AZUL,
                                                  style=_sombra_texto(True)),
                                          ft.Text(sub, size=12, color=SUAVE)], spacing=2, expand=True)]),
                       padding=12)

    def _redactor(self, vista: str, lineas=1, etiqueta="Escribe tu mensaje…"):
        entrada = campo("", hint_text=etiqueta, multiline=True, min_lines=lineas, max_lines=5, shift_enter=True,
                        border_radius=26, expand=True, content_padding=ft.padding.symmetric(horizontal=18, vertical=12))
        entrada.label = None

        def mandar(_=None):
            texto = (entrada.value or "").strip()
            entrada.value = ""
            self.enviar(vista, texto)

        entrada.on_submit = mandar
        icono = I.CALL_ROUNDED if vista == "llamadas" else I.SEND_ROUNDED
        enviar = ft.Container(icono_redondo(icono, VERDE if vista == "llamadas" else TURQUESA, 52),
                              tooltip="Llamar" if vista == "llamadas" else "Enviar", on_click=mandar,
                              animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT), scale=1,
                              on_hover=_relieve_hover)
        enviar.data = "enviar"
        return tarjeta(ft.Row([entrada, enviar], vertical_alignment=ft.CrossAxisAlignment.END), padding=10)

    def _campo_contacto(self, clave: str, etiqueta: str, icono, col):
        c = campo(etiqueta, self.contacto[clave], prefix_icon=icono, dense=True, col=col)

        def cambio(e):
            self.contacto[clave] = e.control.value or ""

        c.on_change = cambio
        if clave in ("whatsapp", "telegram", "llamadas", "correo"):
            c.on_blur = lambda _: self._pintar_mensajes(clave)   # muestra la conversación de ese contacto
        return c

    def _chips(self, vista):
        return ft.Row([self._chip_pregunta(e, t) for e, t in SUGERIDAS[:6]], wrap=True, spacing=6, run_spacing=8)

    def _lista(self, vista: str, bienvenida: str):
        self.refs[f"bienvenida_{vista}"] = bienvenida
        lista = ft.ListView(expand=True, spacing=12, padding=ft.padding.symmetric(vertical=10), auto_scroll=True)
        self.refs[f"lista_{vista}"] = lista
        return lista

    def _mesa(self, lista):
        """Área de conversación hundida en la página."""
        return ft.Container(lista, expand=True, border_radius=18, padding=12,
                            gradient=_degradado("#E8E1D3", "#F3EEE4", "#F7F3EA"), border=ft.border.all(1, "#C9C1B0"))

    # ------------------------------------------------------------- WhatsApp / Telegram
    def _chat(self, vista: str):
        nombre = next(n for c, _, n, _, _ in CANALES_UI if c == vista)
        lista = self._lista(vista, f"Escribe tu duda sobre la titulación por {nombre}. "
                                   "También puedes tocar una pregunta frecuente.")
        etiqueta = "Tu teléfono o @usuario" if vista == "telegram" else "Tu teléfono"
        columna = ft.Column([
            self._encabezado_canal(vista, f"{nombre} · Coordinación de Titulación", "En línea · respuesta inmediata"),
            ft.ResponsiveRow([self._campo_contacto(vista, etiqueta, I.PHONE_ANDROID, {"xs": 12, "sm": 6}),
                              self._campo_contacto("perfil", "Tu nombre de perfil", I.PERSON_OUTLINE, {"xs": 12, "sm": 6})],
                             spacing=10, run_spacing=10),
            self._mesa(lista),
            self._chips(vista),
            self._redactor(vista),
        ], spacing=12, expand=True)
        self._pintar_diferido(vista)
        return columna

    # ------------------------------------------------------------- Correo
    def _correo(self):
        prov = self.contacto["proveedor"]

        def cambiar(p):
            self.contacto["proveedor"] = p
            self.render()

        botones = ft.Row([
            boton("Gmail", lambda _: cambiar("gmail"), I.MAIL_ROUNDED, color="azul" if prov == "gmail" else "claro", alto=42),
            boton("Outlook", lambda _: cambiar("outlook"), I.ALTERNATE_EMAIL,
                  color="azul" if prov == "outlook" else "claro", alto=42),
        ], spacing=8)
        asunto = campo("Asunto", self.contacto["asunto"], prefix_icon=I.SUBJECT, dense=True, col={"xs": 12, "md": 6})
        asunto.on_change = lambda e: self.contacto.__setitem__("asunto", e.control.value or "")
        lista = self._lista("correo", "Escribe un correo a la Coordinación de Titulación. Te responderemos con el "
                                      "mismo asunto, saludo y firma.")
        columna = ft.Column([
            self._encabezado_canal("correo", "Correo · Coordinación de Titulación", "Respuesta con el mismo asunto"),
            botones,
            ft.ResponsiveRow([self._campo_contacto("correo", "De (tu correo)", I.PERSON_OUTLINE, {"xs": 12, "md": 6}),
                              asunto], spacing=10, run_spacing=10),
            self._mesa(lista),
            self._redactor("correo", 2, "Escribe tu correo…"),
        ], spacing=12, expand=True)
        self._pintar_diferido("correo")
        return columna

    # ------------------------------------------------------------- Llamadas
    def _llamadas(self):
        lista = self._lista("llamadas", "Aquí verás tus llamadas y el mensaje de texto con el que te respondimos.")
        duracion = campo("Duración (segundos)", self.contacto["duracion"], prefix_icon=I.TIMER_OUTLINED, dense=True,
                         keyboard_type=ft.KeyboardType.NUMBER, col={"xs": 12, "sm": 6})
        duracion.on_change = lambda e: self.contacto.__setitem__("duracion", e.control.value or "0")
        columna = ft.Column([
            self._encabezado_canal("llamadas", "Llamadas · Coordinación de Titulación",
                                   "Te contestamos por mensaje de texto al mismo número"),
            ft.ResponsiveRow([self._campo_contacto("llamadas", "Número que llama", I.PHONE_ANDROID, {"xs": 12, "sm": 6}),
                              duracion], spacing=10, run_spacing=10),
            self._mesa(lista),
            ft.Text("Escribe lo que dijiste en la llamada (o déjalo vacío si colgaste) y pulsa el teléfono verde.",
                    size=12, color=SUAVE),
            self._redactor("llamadas", 1, "Lo que dijiste en la llamada…"),
        ], spacing=12, expand=True)
        self._pintar_diferido("llamadas")
        return columna

    # ==================================================================
    #  Coordinación (descarga del Excel)
    # ==================================================================
    def _ir_coordinacion(self):
        self.pantalla = "coordinacion"
        self.render()

    def _coordinacion(self):
        ancho = min(560, self.ancho - 32)
        if not self.coord_ok:
            clave = campo("Contraseña de la Coordinación", password=True, can_reveal_password=True,
                          prefix_icon=I.LOCK_OUTLINE, autofocus=True)

            def entrar(_=None):
                if self.clave and hmac.compare_digest((clave.value or "").encode(), self.clave.encode()):
                    self.coord_ok = True
                    self.render()
                else:
                    clave.error_text = "Contraseña incorrecta."
                    self.page.update()

            clave.on_submit = entrar
            contenido = [ft.Row([icono_redondo(I.ADMIN_PANEL_SETTINGS_ROUNDED, INDIGO, 68)], alignment=ft.MainAxisAlignment.CENTER),
                         self._titulo("Acceso Coordinación", "Solo para el personal de la Coordinación de Titulación."),
                         clave, ft.Row([boton("Entrar", entrar, I.LOGIN_ROUNDED, color="azul", expand=True)])]
        else:
            ruta = self.bot.excel.ruta
            info = (f"{ruta.name} · {ruta.stat().st_size / 1024:.0f} KB · actualizado "
                    f"{datetime.fromtimestamp(ruta.stat().st_mtime):%d/%m/%Y %H:%M}") if ruta.exists() else "Sin archivo"
            contenido = [ft.Row([icono_redondo(I.TABLE_VIEW_ROUNDED, EXCEL_VERDE, 68)], alignment=ft.MainAxisAlignment.CENTER),
                         self._titulo("Excel de la Coordinación",
                                      "Descarga el archivo con las hojas Alumno, Requisitos, No Adeudo, Mensajes, "
                                      "Llamadas y Pendientes."),
                         tarjeta(ft.Text(info, size=12, color=AZUL), padding=12)]
            if self.modo_ejecucion == "demo":
                contenido.append(ft.Container(ft.Text(
                    "Esta es la versión de demostración: los datos se quedan en este navegador y no se juntan en un "
                    "Excel central. Usa la versión publicada en el servidor para el uso real.", size=12, color="#B26A00"),
                    gradient=_degradado("#FFF9F0", "#FCE9CF"), border=ft.border.all(1, "#EBCB98"), border_radius=12,
                    padding=12))
            else:
                contenido.append(ft.Row([boton("Descargar Excel", lambda _: self._descargar(), I.DOWNLOAD_ROUNDED,
                                               color="excel", expand=True)]))
            if self.respaldo:
                contenido.append(ft.Text(f"Respaldo en GitHub: {self.respaldo.ultimo}", size=12, color=SUAVE))
            elif self.modo_ejecucion == "servidor":
                contenido.append(ft.Text("⚠ Respaldo en GitHub sin configurar: si el servidor se reinicia se pierden "
                                         "los datos. Revisa la guía de publicación.", size=12, color=ROJO))
        return ft.Container(ft.Column([tarjeta(ft.Column(contenido, spacing=14, tight=True), padding=26, width=ancho),
                                       placa_institucional()],
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=18,
                                      scroll=ft.ScrollMode.AUTO),
                            alignment=ft.alignment.top_center, padding=24, expand=True)

    def _descargar(self):
        origen = self.bot.excel.ruta
        nombre = f"TechMth_Titulacion_{datetime.now():%Y%m%d_%H%M}.xlsx"
        if self.modo_ejecucion == "escritorio" or not self.assets:
            self.page.launch_url(origen.resolve().as_uri())
            return
        carpeta = self.assets / "descargas"
        carpeta.mkdir(parents=True, exist_ok=True)
        limite = time.time() - 15 * 60
        for vieja in carpeta.iterdir():           # los enlaces viejos se borran a los 15 minutos
            if vieja.stat().st_mtime < limite:
                shutil.rmtree(vieja, ignore_errors=True)
        token = uuid.uuid4().hex
        destino = carpeta / token / nombre
        destino.parent.mkdir(parents=True)
        shutil.copy2(origen, destino)
        self.page.launch_url(f"/descargas/{token}/{nombre}", web_window_name="_blank")
        self.aviso("Descarga lista. El enlace vence en 15 minutos.")


def iniciar(page: ft.Page, bot: Bot, **opciones):
    AppTechMth(page, bot, **opciones)
