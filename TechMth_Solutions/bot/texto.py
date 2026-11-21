"""Limpieza de texto y extracción de datos (número de control, correo, teléfono, nombre)."""
from __future__ import annotations

import re
import unicodedata

# Abreviaturas y faltas comunes en mensajes de WhatsApp
_REEMPLAZOS = {
    "q": "que", "k": "que", "ke": "que", "xq": "porque", "pq": "porque", "porq": "porque",
    "tmb": "tambien", "tb": "tambien", "x": "por", "xfa": "por favor", "porfa": "por favor",
    "pls": "por favor", "plis": "por favor", "dnd": "donde", "cuando": "cuando", "info": "informacion",
    "tit": "titulacion", "titu": "titulacion", "ns": "no se", "nc": "no se", "bn": "bien",
    "hla": "hola", "ola": "hola", "holi": "hola", "grax": "gracias", "grx": "gracias",
    "thx": "gracias", "ok": "ok", "sip": "si", "simon": "si", "nel": "no", "nop": "no",
    "comtrol": "control", "nocontrol": "no control", "ncontrol": "no control",
}


def sin_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """minúsculas, sin acentos ni signos, con abreviaturas expandidas."""
    t = sin_acentos((texto or "").lower()).replace("º", "o").replace("°", "o")
    t = re.sub(r"[^a-z0-9@.ñ]+", " ", t)
    t = re.sub(r"(?<![a-z0-9])\.|\.(?![a-z0-9])", " ", t)  # puntos sueltos
    palabras = [_REEMPLAZOS.get(p, p) for p in t.split()]
    # letras repetidas: "holaaaa" → "hola"
    palabras = [re.sub(r"([a-z])\1{2,}", r"\1", p) for p in palabras]
    return " ".join(palabras)


def normalizar_encabezado(texto) -> str:
    t = normalizar(str(texto or ""))
    return t.replace(".", " ").replace("comtrol", "control").strip()


# ------------------------------------------------------------------ entidades
_RE_CONTROL = re.compile(r"(?<![0-9a-z])[a-z]?([0-9]{8})(?![0-9])", re.IGNORECASE)
_RE_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_TELEFONO = re.compile(r"(?:\+?52\s*)?(?:\(?\d{2,3}\)?[\s.-]*)\d{3,4}[\s.-]*\d{4}")


def extraer_num_control(texto: str) -> str | None:
    """8 dígitos, con o sin letra al inicio (L24660999 → 24660999).
    Ignora números que forman parte de un correo o de un teléfono de 10 dígitos."""
    limpio = _RE_CORREO.sub(" ", texto or "")
    for m in _RE_CONTROL.finditer(limpio):
        inicio, fin = m.span()
        antes = limpio[max(0, inicio - 3):inicio]
        despues = limpio[fin:fin + 3]
        if re.search(r"\d[\s-]?$", antes) or re.match(r"^[\s-]?\d", despues):
            continue  # pedazo de un número más largo (teléfono)
        return m.group(1)
    return None


def extraer_correo(texto: str) -> str | None:
    m = _RE_CORREO.search(texto or "")
    return m.group(0).lower() if m else None


def normalizar_telefono(texto) -> str | None:
    digitos = re.sub(r"\D", "", str(texto or ""))
    if len(digitos) < 10:
        return None
    return digitos[-10:]


def extraer_telefono(texto: str) -> str | None:
    sin_correo = _RE_CORREO.sub(" ", texto or "")
    for m in _RE_TELEFONO.finditer(sin_correo):
        tel = normalizar_telefono(m.group(0))
        if tel:
            return tel
    return None


def formatear_telefono(tel10: str | None) -> str:
    if not tel10:
        return ""
    return f"{tel10[:3]} {tel10[3:6]} {tel10[6:]}"


_RE_NOMBRE = re.compile(
    r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){0,4})",
    re.IGNORECASE)
_NO_NOMBRE = {"de", "del", "la", "el", "un", "una", "egresado", "egresada", "alumno", "alumna",
              "estudiante", "ingeniero", "ingeniera", "de la", "nuevo", "nueva"}
_CORTES = {"y", "mi", "con", "de", "del", "numero", "num", "no", "control", "carrera",
           "quiero", "necesito", "tengo", "estudio", "egresado", "egresada", "alumno", "alumna",
           "estudiante", "busco", "me", "por", "para", "favor", "estoy", "ya", "pero", "que"}


def extraer_nombre(texto: str) -> str | None:
    m = _RE_NOMBRE.search(texto or "")
    if not m:
        return None
    palabras = []
    for p in m.group(1).split():
        if sin_acentos(p.lower()) in _CORTES:
            break
        palabras.append(p)
    if not palabras or sin_acentos(palabras[0].lower()) in _NO_NOMBRE:
        return None
    return nombre_propio(" ".join(palabras))


def nombre_propio(texto: str) -> str:
    menores = {"de", "del", "la", "las", "los", "y"}
    partes = re.sub(r"\s+", " ", (texto or "").strip()).split(" ")
    return " ".join(p.lower() if i and p.lower() in menores else p[:1].upper() + p[1:].lower()
                    for i, p in enumerate(partes) if p)


def es_afirmacion(texto: str) -> bool:
    n = normalizar(texto)
    return bool(re.fullmatch(r"(si|sii|claro|correcto|exacto|ok|okay|va|vale|de acuerdo|"
                             r"asi es|esta bien|confirmo|si es|si esta bien|si correcto|"
                             r"si por favor|afirmativo|sale)( .*)?", n)) and not n.startswith("si no")


def es_negacion(texto: str) -> bool:
    n = normalizar(texto)
    return bool(re.fullmatch(r"(no|nop|negativo|para nada|no es|incorrecto|esta mal)( .*)?", n))


def quiere_omitir(texto: str) -> bool:
    n = normalizar(texto)
    return n in {"omitir", "omite", "saltar", "no tengo", "ninguno", "ninguna", "paso",
                 "no", "despues", "luego", "n a", "na"}


def quiere_cancelar(texto: str) -> bool:
    n = normalizar(texto)
    return n in {"cancelar", "cancela", "salir", "olvidalo", "ya no", "detener", "alto", "stop",
                 "menu", "menu principal", "inicio"}
