"""Registro de alumnos desde el portal: valida los datos y los guarda en la hoja Alumno
con el mismo orden y formato que la tabla de la Coordinación:

    Nº Control | Nombre Completo | Carrera | Correo Institucional | Correo Personal | Teléfono
    24660999   | Valeria Torres …| ISC     | L24660999@matehuala…  | …@gmail.com     | 488 000 1234
"""
from __future__ import annotations

import re

from .excel import AlmacenExcel
from .texto import extraer_num_control, formatear_telefono, nombre_propio, normalizar_telefono

CARRERAS = {
    "ISC": "Ingeniería en Sistemas Computacionales",
    "IIND": "Ingeniería Industrial",
    "IGE": "Ingeniería en Gestión Empresarial",
    "IC": "Ingeniería Civil",
    "IEM": "Ingeniería Electromecánica",
}
CAMPOS = [  # orden de la tabla Alumno
    ("num_control", "Nº Control"),
    ("nombre", "Nombre Completo"),
    ("carrera", "Carrera"),
    ("correo_institucional", "Correo Institucional"),
    ("correo_personal", "Correo Personal"),
    ("telefono", "Teléfono"),
]
_CORREO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' ]+$")


def leer_num_control(texto: str) -> str | None:
    """Acepta 24660999 o L24660999; devuelve los 8 dígitos o None."""
    limpio = (texto or "").strip()
    if not re.fullmatch(r"[A-Za-z]?\d{8}", limpio):
        return None
    return extraer_num_control(limpio)


def correo_sugerido(num: str) -> str:
    return f"L{num}@matehuala.tecnm.mx"


def buscar(almacen: AlmacenExcel, num: str) -> dict | None:
    return almacen.buscar("Alumno", "num_control", num)


def validar(datos: dict, nuevo: bool = True) -> tuple[dict, dict]:
    """Devuelve (datos limpios, errores por campo). En una actualización (nuevo=False)
    los campos vacíos se ignoran para conservar el dato actual."""
    limpios, errores = {}, {}

    nombre = re.sub(r"\s+", " ", (datos.get("nombre") or "").strip())
    if nombre:
        if not _LETRAS.match(nombre) or len(nombre.split()) < 2:
            errores["nombre"] = "Escribe tu nombre y apellidos, solo con letras."
        else:
            limpios["nombre"] = nombre_propio(nombre)
    elif nuevo:
        errores["nombre"] = "Este dato es obligatorio."

    carrera = (datos.get("carrera") or "").strip().split(" ")[0].upper()
    if carrera:
        if carrera not in CARRERAS:
            errores["carrera"] = "Elige tu carrera de la lista."
        else:
            limpios["carrera"] = carrera
    elif nuevo:
        errores["carrera"] = "Elige tu carrera."

    inst = (datos.get("correo_institucional") or "").strip()
    if inst:
        if not _CORREO.match(inst):
            errores["correo_institucional"] = "Escribe un correo válido."
        elif not inst.lower().endswith("tecnm.mx"):
            errores["correo_institucional"] = "Debe ser tu correo del Tec (…@matehuala.tecnm.mx)."
        else:
            usuario, dominio = inst.split("@")
            limpios["correo_institucional"] = (usuario[:1].upper() + usuario[1:] if usuario[:1].lower() == "l"
                                               else usuario) + "@" + dominio.lower()
    elif nuevo:
        errores["correo_institucional"] = "Este dato es obligatorio."

    personal = (datos.get("correo_personal") or "").strip()
    if personal:
        if not _CORREO.match(personal):
            errores["correo_personal"] = "Escribe un correo válido o déjalo vacío."
        else:
            limpios["correo_personal"] = personal.lower()

    tel = (datos.get("telefono") or "").strip()
    if tel:
        digitos = re.sub(r"\D", "", tel)
        if len(digitos) not in (10, 12) or (len(digitos) == 12 and not digitos.startswith("52")):
            errores["telefono"] = "Escribe tu celular a 10 dígitos."
        else:
            limpios["telefono"] = formatear_telefono(normalizar_telefono(digitos))
    elif nuevo:
        errores["telefono"] = "Escribe tu celular a 10 dígitos."
    return limpios, errores


def guardar(almacen: AlmacenExcel, num: str, limpios: dict, nuevo: bool) -> bool:
    """Escribe en Alumno y, si es nuevo, crea su fila en Requisitos y No Adeudo.
    Devuelve False si el Excel estaba ocupado y los datos quedaron en espera."""
    if nuevo:
        fila = {clave: limpios.get(clave, "") for clave, _ in CAMPOS if clave != "num_control"}
        ok = almacen.actualizar("Alumno", "num_control", num, fila)
        for hoja in ("Requisitos", "No Adeudo"):
            if not almacen.buscar(hoja, "num_control", num):
                ok = almacen.agregar(hoja, {"num_control": num, "nombre": limpios["nombre"]}) and ok
        return ok
    if not limpios:
        return True
    ok = almacen.actualizar("Alumno", "num_control", num, limpios, crear=False)
    if "nombre" in limpios:
        for hoja in ("Requisitos", "No Adeudo"):
            ok = almacen.actualizar(hoja, "num_control", num, {"nombre": limpios["nombre"]}, crear=False) and ok
    return ok


def fila_para_mostrar(num: str, limpios: dict) -> list[str]:
    return [num] + [limpios.get(clave, "") for clave, _ in CAMPOS[1:]]
