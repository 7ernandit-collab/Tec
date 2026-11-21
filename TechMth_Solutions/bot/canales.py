"""Mensajes que entran y salen por cada canal, y su formato."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

CANALES = {
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "gmail": "Gmail",
    "outlook": "Outlook",
    "llamada": "Llamada",
    "sms": "SMS",
}
CORREOS = {"gmail", "outlook"}
TELEFONICOS = {"whatsapp", "telegram", "llamada", "sms"}


@dataclass
class MensajeEntrante:
    canal: str                      # whatsapp | telegram | gmail | outlook | llamada | sms
    remitente: str                  # número de teléfono o correo
    texto: str = ""                 # mensaje, cuerpo del correo o lo que dijo en la llamada
    asunto: str = ""                # solo correos
    nombre_mostrado: str = ""       # nombre del perfil de WhatsApp o del correo
    duracion: int = 0               # solo llamadas (segundos)
    fecha: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))


@dataclass
class Respuesta:
    canal: str                      # canal por el que se envía (las llamadas se contestan por texto)
    para: str
    texto: str
    asunto: str = ""
    intencion: str = ""
    atendido_por: str = "Bot"


_CITA = re.compile(r"^(>|el .+ escribi[oó]:|on .+ wrote:|-{2,}\s*original|de:\s|from:\s|enviado desde)",
                   re.IGNORECASE)


def limpiar_correo(cuerpo: str) -> str:
    """Quita el historial citado y la firma de un correo."""
    lineas = []
    for linea in (cuerpo or "").splitlines():
        if _CITA.match(linea.strip()):
            break
        if linea.strip() in ("--", "-- "):
            break
        lineas.append(linea)
    return "\n".join(lineas).strip()


def para_correo(texto: str) -> str:
    """El formato *negritas* de WhatsApp no aplica en correo."""
    return re.sub(r"\*(\S[^*]*\S|\S)\*", r"\1", texto)


def para_sms(texto: str) -> str:
    return para_correo(texto)
