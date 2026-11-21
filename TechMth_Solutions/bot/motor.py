"""Motor de atención automatizada de la Coordinación de Titulación (TechMth Solutions).

Recibe un mensaje de cualquier canal, entiende qué pregunta el usuario, responde por texto
de forma natural y guarda en Excel lo que se recibió (Mensajes, Llamadas, Pendientes y,
cuando el alumno da sus datos, Alumno / Requisitos / No Adeudo).
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .canales import (CANALES, CORREOS, TELEFONICOS, MensajeEntrante, Respuesta, limpiar_correo,
                      para_correo, para_sms)
from . import avance
from .excel import AlmacenExcel
from .nlu import Clasificador
from .texto import (es_afirmacion, es_negacion, extraer_correo, extraer_nombre, extraer_num_control,
                    extraer_telefono, formatear_telefono, nombre_propio, normalizar,
                    normalizar_telefono, quiere_cancelar, quiere_omitir)

DURACION_SESION = timedelta(minutes=30)

CAMPOS_REGISTRO = [
    ("num_control", "tu *número de control* (8 dígitos)"),
    ("nombre", "tu *nombre completo*"),
    ("carrera", "tu *carrera* (por ejemplo ISC, IIND, IGE)"),
    ("correo_institucional", "tu *correo institucional*"),
    ("correo_personal", "tu *correo personal* (o escribe *omitir*)"),
    ("telefono", "tu *número de celular* a 10 dígitos (o escribe *omitir*)"),
]
ETIQUETAS = {"num_control": "Nº de control", "nombre": "Nombre", "carrera": "Carrera",
             "correo_institucional": "Correo institucional", "correo_personal": "Correo personal",
             "telefono": "Teléfono"}
CAMPOS_ACTUALIZABLES = {
    "correo personal": "correo_personal", "correo institucional": "correo_institucional",
    "telefono": "telefono", "celular": "telefono", "numero": "telefono", "carrera": "carrera",
    "nombre": "nombre", "correo": "correo_personal",
}
REQUISITOS = [("creditos", "5 créditos complementarios"), ("servicio_social", "Servicio social"),
              ("ingles", "Inglés acreditado")]
AREAS = [("recursos_financieros", "Recursos Financieros"), ("coordinador", "Coordinador"),
         ("biblioteca", "Biblioteca"), ("centro_informacion", "Centro de Información"),
         ("almacen", "Almacén")]


@dataclass
class Sesion:
    clave: str
    ultimo: datetime = field(default_factory=datetime.now)
    turnos: int = 0
    alumno: dict | None = None        # fila de la hoja Alumno, si se identificó
    verificado: bool = False          # el contacto coincide con el registrado
    flujo: str | None = None          # registro | actualizar | estatus | humano
    paso: str | None = None
    datos: dict = field(default_factory=dict)
    nombre: str = ""


def _si_no(valor) -> bool | None:
    n = normalizar(str(valor)) if valor not in (None, "") else ""
    if not n:
        return None
    if n in {"si", "s", "x", "ok", "1", "true", "verdadero", "listo", "liberado", "cumple",
             "acreditado", "completo", "sin adeudo", "firmado"}:
        return True
    if n in {"no", "n", "0", "false", "falso", "pendiente", "adeudo", "con adeudo", "falta"}:
        return False
    return None


def _lista(elementos: list[str]) -> str:
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


class Bot:
    def __init__(self, almacen: AlmacenExcel, ruta_conocimiento: str | Path, semilla=None):
        self.excel = almacen
        self.kb = json.loads(Path(ruta_conocimiento).read_text(encoding="utf-8"))
        self.nlu = Clasificador(self.kb["intenciones"], self.kb["menu"])
        self.azar = random.Random(semilla)
        self.sesiones: dict[str, Sesion] = {}
        self.ahora = lambda: datetime.now().replace(microsecond=0)

    # =========================================================== entrada
    def procesar(self, msg: MensajeEntrante) -> Respuesta:
        sesion = self._sesion(msg)
        texto = limpiar_correo(msg.texto) if msg.canal in CORREOS else (msg.texto or "").strip()
        if msg.canal in CORREOS and msg.asunto and len(normalizar(texto).split()) < 3:
            texto = f"{msg.asunto}. {texto}".strip(". ")

        if msg.canal == "llamada" and not texto:
            intencion, cuerpo, atendido = "llamada", self._llamada_sin_mensaje(sesion), "Bot"
        else:
            intencion, cuerpo, atendido = self._responder(sesion, texto, msg)

        respuesta = self._empaquetar(msg, sesion, intencion, cuerpo, atendido)
        self._guardar(msg, sesion, texto, respuesta)
        sesion.turnos += 1
        sesion.ultimo = self.ahora()
        return respuesta

    def _sesion(self, msg: MensajeEntrante) -> Sesion:
        clave = (normalizar_telefono(msg.remitente) if msg.canal in TELEFONICOS
                 else msg.remitente.strip().lower())
        clave = clave or msg.remitente
        s = self.sesiones.get(clave)
        if s is None or self.ahora() - s.ultimo > DURACION_SESION:
            s = Sesion(clave)
            self.sesiones[clave] = s
        if s.alumno is None:
            alumno = self.excel.buscar_alumno_por_contacto(
                telefono=msg.remitente if msg.canal in TELEFONICOS else None,
                correo=msg.remitente if msg.canal in CORREOS else None)
            if alumno:
                s.alumno, s.verificado = alumno, True
        if s.alumno and s.alumno.get("nombre"):
            s.nombre = str(s.alumno["nombre"]).split()[0]
        elif not s.nombre and msg.nombre_mostrado:
            s.nombre = nombre_propio(msg.nombre_mostrado.split()[0])
        return s

    # ======================================================= razonamiento
    def _responder(self, s: Sesion, texto: str, msg: MensajeEntrante) -> tuple[str, str, str]:
        if s.flujo:
            if quiere_cancelar(texto):
                s.flujo = s.paso = None
                s.datos = {}
                return "cancelar", "Listo, lo dejamos ahí. " + self._menu(msg.canal), "Bot"
            return getattr(self, f"_flujo_{s.flujo}")(s, texto, msg)

        r = self.nlu.clasificar(texto)
        nombre_dicho = extraer_nombre(texto)
        if nombre_dicho and not s.alumno:
            s.nombre = nombre_dicho.split()[0]

        if r.principal is None:
            if r.despedida:
                return "despedida", ("¡Gracias a ti! " if r.gracias else "") + self._frase("despedida", s), "Bot"
            if r.gracias:
                return "gracias", self._frase("gracias", s), "Bot"
            if r.saludo:
                return "saludo", self._frase("saludo", s) + "\n\n" + self._menu(msg.canal), "Bot"
            # ¿mandó solo su número de control o sus datos? → ofrecer estatus
            if extraer_num_control(texto):
                return self._iniciar_estatus(s, texto, msg)
            return ("no_entendido",
                    self._elegir(self.kb["frases"]["no_entendi"], s) + "\n\n" + self._menu(msg.canal),
                    "Pendiente")

        partes = []
        intencion = r.principal
        for i, nombre in enumerate([r.principal] + r.secundarias):
            if nombre in ("estatus", "registro", "humano"):
                if i == 0:
                    return getattr(self, f"_iniciar_{nombre}")(s, texto, msg)
                continue
            partes.append(self._frase(nombre, s, msg.canal))
        cuerpo = "\n\n".join(partes)
        if r.gracias and not r.despedida:
            cuerpo = "¡Con gusto! " + cuerpo
        seguimiento = self._elegir(self.kb["frases"]["seguimiento"], s)
        if seguimiento and intencion not in ("menu", "despedida"):
            cuerpo += "\n\n" + seguimiento
        return intencion, cuerpo, "Bot"

    # ---------------------------------------------------------- frases
    def _elegir(self, opciones: list[str], s: Sesion) -> str:
        texto = self.azar.choice(opciones)
        return self._rellenar(texto, s)

    def _rellenar(self, texto: str, s: Sesion) -> str:
        c = self.kb["contacto"]
        return (texto.replace("{nombre_coma}", f", {s.nombre}" if s.nombre else "")
                .replace("{nombre}", s.nombre or "")
                .replace("{correo}", c["correo"]).replace("{extension}", c["extension"])
                .replace("{lugar}", c["lugar"]))

    def _frase(self, intencion: str, s: Sesion, canal: str = "whatsapp") -> str:
        respuestas = self.kb["intenciones"][intencion]["respuestas"]
        texto = self._elegir(respuestas, s)
        if "{menu}" in texto:
            texto = texto.replace("{menu}", self._menu(canal))
        return texto

    def _menu(self, canal: str) -> str:
        lineas = ["Puedo ayudarte con:"]
        for num, _, etiqueta in self.kb["menu"]:
            lineas.append(f"*{num}.* {etiqueta}")
        lineas.append("Escribe el número o tu pregunta con tus palabras.")
        return "\n".join(lineas)

    @staticmethod
    def _saludo_hora(hora: int) -> str:
        if hora < 12:
            return "Buenos días"
        if hora < 19:
            return "Buenas tardes"
        return "Buenas noches"

    def _llamada_sin_mensaje(self, s: Sesion) -> str:
        return ("Recibimos tu llamada a la Coordinación de Titulación y no pudimos atenderla en "
                "ese momento. Por aquí puedo resolver tus dudas al instante.\n\n" + self._menu("sms"))

    # ======================================================= estatus
    def _iniciar_estatus(self, s: Sesion, texto: str, msg: MensajeEntrante):
        num = extraer_num_control(texto)
        if s.alumno and s.verificado and (not num or num == self._num(s.alumno)):
            return "estatus", self._estatus(s.alumno, s), "Bot"
        if num:
            return self._estatus_con_numero(s, num, msg)
        s.flujo, s.paso = "estatus", "num_control"
        return ("estatus", "Con gusto reviso tu avance. ¿Me compartes tu *número de control*?",
                "Bot")

    def _flujo_estatus(self, s: Sesion, texto: str, msg: MensajeEntrante):
        num = extraer_num_control(texto)
        if not num:
            return ("estatus", "No encontré un número de control en tu mensaje 🤔. Son 8 dígitos, "
                               "por ejemplo 24660999. ¿Me lo escribes de nuevo? (o *cancelar*)", "Bot")
        s.flujo = s.paso = None
        return self._estatus_con_numero(s, num, msg)

    def _estatus_con_numero(self, s: Sesion, num: str, msg: MensajeEntrante):
        alumno = self.excel.buscar("Alumno", "num_control", num)
        if not alumno:
            s.flujo, s.paso = "registro", "confirmar_inicio"
            s.datos = {"num_control": num}
            return ("estatus", f"No tengo registrado el número de control {num}. ¿Quieres que te "
                               f"registre ahora? Solo toma un minuto. Responde *sí* o *no*.", "Bot")
        if not self._contacto_coincide(alumno, msg):
            self._pendiente(msg, num, "Pidió estatus desde un contacto distinto al registrado")
            return ("estatus",
                    "Por seguridad solo puedo compartir el avance del trámite al teléfono o correo "
                    "que el alumno tiene registrado. Escríbeme desde ese contacto, o pide a la "
                    f"Coordinación que actualice tus datos: {self.kb['contacto']['correo']}.",
                    "Pendiente")
        s.alumno, s.verificado = alumno, True
        s.nombre = str(alumno.get("nombre") or "").split()[0] if alumno.get("nombre") else s.nombre
        return "estatus", self._estatus(alumno, s), "Bot"

    @staticmethod
    def _num(fila: dict | None) -> str:
        if not fila or fila.get("num_control") in (None, ""):
            return ""
        v = fila["num_control"]
        return str(int(v)) if isinstance(v, float) else str(v).strip()

    @staticmethod
    def _contacto_coincide(alumno: dict, msg: MensajeEntrante) -> bool:
        if msg.canal in TELEFONICOS:
            return bool(normalizar_telefono(msg.remitente)) and \
                normalizar_telefono(alumno.get("telefono")) == normalizar_telefono(msg.remitente)
        correo = msg.remitente.strip().lower()
        return correo in {str(alumno.get("correo_institucional") or "").strip().lower(),
                          str(alumno.get("correo_personal") or "").strip().lower()}

    def _estatus(self, alumno: dict, s: Sesion) -> str:
        av = avance.calcular(self.excel, self._num(alumno))
        lineas = [f"Revisé tu avance de titulación ({av['completos']} de {av['total']} listos) 👇", "",
                  "*Requisitos*"]
        for etiqueta, v in av["requisitos"]:
            lineas.append(f"✅ {etiqueta}" if v is True else
                          f"❌ {etiqueta}: pendiente" if v is False else
                          f"❔ {etiqueta}: sin registro todavía")
        firmadas = [e for e, v in av["firmas"] if v is True]
        lineas += ["", "*Carta de no adeudo*"]
        if firmadas:
            lineas.append(f"✅ Ya firmaron: {avance.lista(firmadas)}")
        if av["firmas_faltan"]:
            lineas.append(f"⏳ Falta: {avance.lista(av['firmas_faltan'])}")
        lineas.append("")
        if av["listo_hoja"] is True and not av["falta_req"] and not av["listo"]:
            lineas.append("Tus requisitos académicos están completos y la Coordinación ya te marcó como "
                          "«Listo para Titular».")
        lineas.append("*Ruta para concluir tu titulación* (sigue estos pasos en orden):")
        for n, (titulo, detalle, hecho) in enumerate(av["pasos"], start=1):
            lineas.append(f"{'✅' if hecho else f'{n}.'} *{titulo}.* {detalle}")
        return "\n".join(lineas)

    # ======================================================= registro
    def _iniciar_registro(self, s: Sesion, texto: str, msg: MensajeEntrante):
        n = normalizar(texto)
        if s.alumno and s.verificado:
            campo = next((v for k, v in CAMPOS_ACTUALIZABLES.items() if k in n), None)
            s.flujo, s.datos = "actualizar", {}
            if campo:
                s.paso = campo
                return ("registro", f"Claro. ¿Cuál es tu nuevo dato de *{ETIQUETAS[campo].lower()}*?",
                        "Bot")
            s.paso = "campo"
            return ("registro", "Ya tengo tu registro 👍\n\n" + self._ficha(s.alumno) +
                    "\n\n¿Qué dato quieres actualizar? (correo personal, correo institucional, "
                    "teléfono o carrera)", "Bot")
        s.flujo, s.datos = "registro", {}
        self._capturar_datos(s, texto, msg)
        return "registro", "Con gusto te registro; es rápido. " + self._siguiente_pregunta(s, msg), "Bot"

    def _capturar_datos(self, s: Sesion, texto: str, msg: MensajeEntrante):
        """Toma cualquier dato que venga en el mensaje o en el canal."""
        d = s.datos
        if (num := extraer_num_control(texto)) and "num_control" not in d:
            d["num_control"] = num
        if (nombre := extraer_nombre(texto)) and "nombre" not in d:
            d["nombre"] = nombre
        if (carrera := self._carrera(texto, solo_clara=True)) and "carrera" not in d:
            d["carrera"] = carrera
        if (correo := extraer_correo(texto)):
            clave = "correo_institucional" if correo.endswith("tecnm.mx") else "correo_personal"
            d.setdefault(clave, correo)
        if (tel := extraer_telefono(texto)) and "telefono" not in d:
            d["telefono"] = tel
        # datos del canal por el que escribe
        if msg.canal in TELEFONICOS and normalizar_telefono(msg.remitente):
            d.setdefault("telefono", normalizar_telefono(msg.remitente))
        if msg.canal in CORREOS:
            correo = msg.remitente.strip().lower()
            clave = "correo_institucional" if correo.endswith("tecnm.mx") else "correo_personal"
            d.setdefault(clave, correo)

    def _carrera(self, texto: str, solo_clara: bool = False) -> str | None:
        n = f" {normalizar(texto)} "
        for clave, alias in self.kb["carreras"].items():
            for a in sorted(alias, key=len, reverse=True):
                if solo_clara and len(a) <= 3 and a != clave.lower():
                    continue
                if f" {a} " in n:
                    return clave
        return None

    def _siguiente_pregunta(self, s: Sesion, msg: MensajeEntrante) -> str:
        d = s.datos
        for campo, pregunta in CAMPOS_REGISTRO:
            if campo in d:
                continue
            s.paso = campo
            if campo == "correo_institucional" and d.get("num_control"):
                sugerido = f"L{d['num_control']}@matehuala.tecnm.mx"
                d["_sugerido"] = sugerido
                return f"¿Tu correo institucional es *{sugerido}*? Responde *sí* o escríbeme el correcto."
            if campo == "nombre" and s.nombre and msg.nombre_mostrado:
                return f"¿Me escribes {pregunta}? (con apellidos, como aparece en tu kárdex)"
            return f"¿Me compartes {pregunta}?"
        s.paso = "confirmar"
        return ("Revisa que tus datos estén bien:\n\n" + self._ficha(d) +
                "\n\n¿Los guardo? Responde *sí* para guardar o *no* para corregir.")

    @staticmethod
    def _ficha(d: dict) -> str:
        filas = []
        for campo, _ in CAMPOS_REGISTRO:
            valor = d.get(campo)
            if campo == "telefono":
                valor = formatear_telefono(normalizar_telefono(valor)) if valor else None
            if campo == "num_control" and isinstance(valor, float):
                valor = int(valor)
            filas.append(f"• {ETIQUETAS[campo]}: {valor or '—'}")
        return "\n".join(filas)

    def _flujo_registro(self, s: Sesion, texto: str, msg: MensajeEntrante):
        d, paso = s.datos, s.paso
        if paso == "confirmar_inicio":
            if es_afirmacion(texto):
                self._capturar_datos(s, "", msg)
                return "registro", "¡Va! " + self._siguiente_pregunta(s, msg), "Bot"
            s.flujo = s.paso = None
            return "registro", "Está bien. " + self._menu(msg.canal), "Bot"

        if paso == "confirmar":
            if es_afirmacion(texto):
                return self._guardar_registro(s, msg)
            if es_negacion(texto) or "corregir" in normalizar(texto):
                s.paso = "corregir"
                return ("registro", "¿Qué dato corrijo? (nombre, carrera, correo institucional, "
                                    "correo personal o teléfono)", "Bot")
            return "registro", "Responde *sí* para guardar o *no* para corregir algún dato.", "Bot"

        if paso == "corregir":
            campo = next((v for k, v in CAMPOS_ACTUALIZABLES.items() if k in normalizar(texto)), None)
            if not campo:
                return "registro", "No identifiqué el dato. Escribe por ejemplo *teléfono* o *carrera*.", "Bot"
            d.pop(campo, None)
            s.paso = campo
            return "registro", f"Va, escríbeme {dict(CAMPOS_REGISTRO)[campo]}.", "Bot"

        error = self._tomar_valor(d, paso, texto)
        if error:
            return "registro", error, "Bot"
        return "registro", self._siguiente_pregunta(s, msg), "Bot"

    def _tomar_valor(self, d: dict, campo: str, texto: str) -> str | None:
        """Guarda el valor de un campo en `d`; devuelve un mensaje si no es válido."""
        if campo == "num_control":
            num = extraer_num_control(texto)
            if not num:
                return "El número de control tiene 8 dígitos (por ejemplo 24660999). ¿Me lo escribes otra vez?"
            existente = self.excel.buscar("Alumno", "num_control", num)
            d["num_control"] = num
            d["_existente"] = bool(existente)
        elif campo == "nombre":
            limpio = re.sub(r"(?i)^(me llamo|mi nombre es|soy)\s+", "", texto.strip())
            limpio = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]", "", limpio).strip()
            if len(limpio.split()) < 2:
                return "¿Me lo escribes con nombre y apellidos, por favor?"
            d["nombre"] = nombre_propio(limpio)
        elif campo == "carrera":
            carrera = self._carrera(texto)
            if not carrera:
                opciones = ", ".join(self.kb["carreras"])
                return f"No reconocí la carrera. Escribe una de estas claves: {opciones}."
            d["carrera"] = carrera
        elif campo == "correo_institucional":
            if es_afirmacion(texto) and d.get("_sugerido"):
                d["correo_institucional"] = d["_sugerido"]
            else:
                correo = extraer_correo(texto)
                if not correo:
                    return "No encontré un correo válido. Escríbelo completo, por ejemplo L24660999@matehuala.tecnm.mx"
                d["correo_institucional"] = correo
        elif campo == "correo_personal":
            if quiere_omitir(texto):
                d["correo_personal"] = ""
            else:
                correo = extraer_correo(texto)
                if not correo:
                    return "Ese correo no parece válido. Escríbelo completo o responde *omitir*."
                d["correo_personal"] = correo
        elif campo == "telefono":
            if quiere_omitir(texto):
                d["telefono"] = ""
            else:
                tel = extraer_telefono(texto) or normalizar_telefono(texto)
                if not tel:
                    return "El número debe tener 10 dígitos. ¿Me lo escribes de nuevo? (o *omitir*)"
                d["telefono"] = tel
        return None

    def _guardar_registro(self, s: Sesion, msg: MensajeEntrante):
        d = s.datos
        num = d["num_control"]
        existente = self.excel.buscar("Alumno", "num_control", num)
        if existente and not self._contacto_coincide(existente, msg):
            self._pendiente(msg, num, "Intento de registro con un número de control que ya existe, "
                                      "desde otro contacto. Verificar identidad.")
            s.flujo = s.paso = None
            s.datos = {}
            return ("registro", "Ese número de control ya está registrado con otros datos de contacto. "
                                "Por seguridad no lo modifiqué; pasé tu caso a la Coordinación para "
                                "que lo verifique y te contacte. 🙌", "Pendiente")
        fila = {k: d.get(k, "") for k, _ in CAMPOS_REGISTRO if k != "num_control"}
        fila["telefono"] = formatear_telefono(normalizar_telefono(fila["telefono"])) if fila["telefono"] else ""
        guardado = self.excel.actualizar("Alumno", "num_control", num, fila)
        for hoja in ("Requisitos", "No Adeudo"):
            if not self.excel.buscar(hoja, "num_control", num):
                self.excel.agregar(hoja, {"num_control": num, "nombre": fila["nombre"]})
        s.alumno = {"num_control": num, **fila}
        s.verificado = True
        s.nombre = fila["nombre"].split()[0]
        s.flujo = s.paso = None
        s.datos = {}
        aviso = "" if guardado else ("\n\n(El archivo de Excel está abierto en otra computadora; "
                                    "tus datos quedaron en espera y se guardarán en cuanto se libere.)")
        return ("registro", f"¡Listo, {s.nombre}! Tus datos quedaron registrados ✅. Cuando la "
                            "Coordinación capture tus requisitos podrás consultar tu avance escribiendo "
                            "*6*." + aviso, "Bot")

    def _flujo_actualizar(self, s: Sesion, texto: str, msg: MensajeEntrante):
        if s.paso == "campo":
            campo = next((v for k, v in CAMPOS_ACTUALIZABLES.items() if k in normalizar(texto)), None)
            if not campo:
                return ("registro", "¿Qué dato cambio? Escribe *correo personal*, *correo institucional*, "
                                    "*teléfono* o *carrera*.", "Bot")
            s.paso = campo
            return "registro", f"De acuerdo. ¿Cuál es tu nuevo dato de *{ETIQUETAS[campo].lower()}*?", "Bot"
        campo = s.paso
        error = self._tomar_valor(s.datos, campo, texto)
        if error:
            return "registro", error, "Bot"
        valor = s.datos[campo]
        if campo == "telefono" and valor:
            valor = formatear_telefono(valor)
        num = self._num(s.alumno)
        self.excel.actualizar("Alumno", "num_control", num, {campo: valor}, crear=False)
        s.alumno[campo] = valor
        s.flujo = s.paso = None
        s.datos = {}
        return ("registro", f"Listo, actualicé tu {ETIQUETAS[campo].lower()} ✅. ¿Algo más en lo que te "
                            "ayude?", "Bot")

    # ======================================================= humano
    def _iniciar_humano(self, s: Sesion, texto: str, msg: MensajeEntrante):
        palabras = normalizar(texto).split()
        if len(palabras) >= 10:  # ya explicó su caso
            return self._flujo_humano(s, texto, msg)
        s.flujo, s.paso = "humano", "detalle"
        return ("humano", "Claro, te paso con una persona de la Coordinación. Para que te atiendan más "
                          "rápido, cuéntame en un mensaje cuál es tu caso.", "Bot")

    def _flujo_humano(self, s: Sesion, texto: str, msg: MensajeEntrante):
        s.flujo = s.paso = None
        num = self._num(s.alumno) or extraer_num_control(texto) or ""
        self._pendiente(msg, num, "Solicita atención de una persona", texto)
        c = self.kb["contacto"]
        return ("humano", "Gracias. Ya dejé tu caso con la Coordinación de Titulación y te contactarán "
                          f"por este medio. Si es urgente, también puedes escribir a {c['correo']} o "
                          f"llamar a la extensión {c['extension']}.", "Pendiente")

    # ======================================================= salida
    def _empaquetar(self, msg: MensajeEntrante, s: Sesion, intencion: str, cuerpo: str,
                    atendido: str) -> Respuesta:
        primera = s.turnos == 0
        if msg.canal in CORREOS:
            saludo = f"Hola{', ' + s.nombre if s.nombre else ''}:"
            if s.nombre:  # el nombre ya va en el saludo del correo
                cuerpo = cuerpo.replace(f", {s.nombre}", "", 1)
            texto = para_correo(f"{saludo}\n\n{cuerpo}\n\nSaludos cordiales,\n{self.kb['bot']['firma_correo']}")
            asunto = (f"Re: {msg.asunto}" if msg.asunto and not msg.asunto.lower().startswith("re:")
                      else msg.asunto or "Respuesta a tu consulta de titulación")
            return Respuesta(msg.canal, msg.remitente, texto, asunto, intencion, atendido)

        hola = ""
        if primera and intencion not in ("saludo", "despedida"):
            hola = f"¡{self._saludo_hora(msg.fecha.hour)}{', ' + s.nombre if s.nombre else ''}! "
        if msg.canal == "llamada":
            # Las llamadas se contestan por mensaje de texto (WhatsApp) al mismo número
            if (msg.texto or "").strip():
                hola = (hola or "¡Hola! ") + "Te escribe la Coordinación de Titulación sobre tu llamada.\n\n"
            return Respuesta("whatsapp", msg.remitente, hola + cuerpo, "", intencion, atendido)
        cuerpo = hola + cuerpo
        if msg.canal == "sms":
            cuerpo = para_sms(cuerpo)
        return Respuesta(msg.canal, msg.remitente, cuerpo, "", intencion, atendido)

    def _guardar(self, msg: MensajeEntrante, s: Sesion, texto: str, r: Respuesta):
        num = self._num(s.alumno) or s.datos.get("num_control") or extraer_num_control(texto) or ""
        nombre = (str(s.alumno.get("nombre")) if s.alumno and s.alumno.get("nombre")
                  else msg.nombre_mostrado or s.nombre)
        remitente = (formatear_telefono(normalizar_telefono(msg.remitente))
                     if msg.canal in TELEFONICOS and normalizar_telefono(msg.remitente) else msg.remitente)
        if msg.canal == "llamada":
            self.excel.agregar("Llamadas", {
                "fecha": msg.fecha, "numero": remitente, "num_control": num, "nombre": nombre,
                "duracion": msg.duracion, "lo_que_dijo": texto, "respuesta": r.texto,
                "enviada_por": CANALES[r.canal]})
        else:
            self.excel.agregar("Mensajes", {
                "fecha": msg.fecha, "canal": CANALES.get(msg.canal, msg.canal), "remitente": remitente,
                "nombre": nombre, "num_control": num, "asunto": msg.asunto, "mensaje": texto,
                "intencion": r.intencion, "respuesta": r.texto, "atendido_por": r.atendido_por})
        if r.intencion == "no_entendido":
            self._pendiente(msg, num, "El bot no entendió la pregunta", texto)

    def _pendiente(self, msg: MensajeEntrante, num: str, motivo: str, texto: str | None = None):
        self.excel.agregar("Pendientes", {
            "fecha": msg.fecha, "canal": CANALES.get(msg.canal, msg.canal), "remitente": msg.remitente,
            "num_control": num, "mensaje": texto if texto is not None else msg.texto,
            "motivo": motivo, "estado": "Pendiente"})
