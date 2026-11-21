"""Datos de ejemplo FICTICIOS (el repositorio es público: no se publican datos reales)."""
from .excel import AlmacenExcel


def cargar_ejemplo(almacen: AlmacenExcel):
    if almacen.buscar("Alumno", "num_control", "24660999"):
        return
    almacen.agregar("Alumno", {"num_control": "24660999", "nombre": "Valeria Torres Ruiz",
                               "carrera": "ISC", "correo_institucional": "L24660999@matehuala.tecnm.mx",
                               "correo_personal": "valeria.demo@gmail.com", "telefono": "488 000 1234"})
    almacen.agregar("Alumno", {"num_control": "24660998", "nombre": "Diego Martínez Silva",
                               "carrera": "IIND"})
    almacen.agregar("Requisitos", {"num_control": "24660999", "nombre": "Valeria Torres Ruiz",
                                   "creditos": "Si", "servicio_social": "Si", "ingles": "Si",
                                   "listo": "Si"})
    almacen.agregar("No Adeudo", {"num_control": "24660999", "nombre": "Valeria Torres Ruiz",
                                  "recursos_financieros": "Si", "coordinador": "No",
                                  "biblioteca": "No", "centro_informacion": "Si", "almacen": "Si"})
