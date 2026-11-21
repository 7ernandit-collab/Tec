"""Avance de titulación de un egresado: lo que ya tiene y lo que le falta.

Se calcula con las hojas Requisitos y No Adeudo que captura la Coordinación.
En No Adeudo, «Si» significa que el área ya firmó (sin adeudo).
"""
from __future__ import annotations

from .excel import AlmacenExcel
from .texto import normalizar

REQUISITOS = [("creditos", "5 créditos complementarios"), ("servicio_social", "Servicio social"),
              ("ingles", "Inglés acreditado")]
AREAS = [("recursos_financieros", "Recursos Financieros"), ("coordinador", "Coordinador"),
         ("biblioteca", "Biblioteca"), ("centro_informacion", "Centro de Información"),
         ("almacen", "Almacén")]
DOCUMENTOS = ("portada del Reporte Final con Vo.Bo. del asesor, anexos 8A, 8B y 9, acta de "
              "calificación de residencias y solicitud del estudiante")


def si_no(valor) -> bool | None:
    n = normalizar(str(valor)) if valor not in (None, "") else ""
    if not n:
        return None
    if n in {"si", "s", "x", "ok", "1", "true", "verdadero", "listo", "liberado", "cumple",
             "acreditado", "completo", "sin adeudo", "firmado"}:
        return True
    if n in {"no", "n", "0", "false", "falso", "pendiente", "adeudo", "con adeudo", "falta"}:
        return False
    return None


def lista(elementos: list[str]) -> str:
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


def _pasos(falta_req: list[str], firmas_faltan: list[str], sin_registro: list[str]) -> list[tuple[str, str, bool]]:
    """Ruta para concluir la titulación: (título, explicación, ¿ya lo cumplió?)."""
    return [
        ("Obtén tus 5 firmas de no adeudo",
         "Recursos Financieros, Coordinador, Biblioteca, Centro de Información y Almacén.",
         not firmas_faltan),
        ("Verifica tus requisitos académicos",
         "5 créditos complementarios, servicio social e inglés acreditado.",
         not falta_req and not sin_registro),
        ("Entrega tu expediente de titulación",
         "Presenta tu Reporte Final, anexos 8A, 8B y 9, acta de calificación de residencias y solicitud "
         "del estudiante.", False),
        ("Confirma la fecha de tu acto protocolario",
         "Espera la revisión de Servicios Escolares, realiza el pago correspondiente y recibe la "
         "confirmación de Coordinación.", False),
    ]


def calcular(almacen: AlmacenExcel, num_control: str) -> dict:
    req = almacen.buscar("Requisitos", "num_control", num_control) or {}
    nad = almacen.buscar("No Adeudo", "num_control", num_control) or {}
    requisitos = [(etiqueta, si_no(req.get(clave))) for clave, etiqueta in REQUISITOS]
    firmas = [(etiqueta, si_no(nad.get(clave))) for clave, etiqueta in AREAS]

    tiene = [e for e, v in requisitos if v is True] + [f"Firma de {e}" for e, v in firmas if v is True]
    falta_req = [e for e, v in requisitos if v is False]
    sin_registro = [e for e, v in requisitos if v is None]
    firmas_faltan = [e for e, v in firmas if v is not True]
    total = len(requisitos) + len(firmas)
    completos = sum(1 for _, v in requisitos + firmas if v is True)

    pasos = _pasos(falta_req, firmas_faltan, sin_registro)
    siguiente = next(titulo for titulo, _, hecho in pasos if not hecho)

    return {
        "requisitos": requisitos, "firmas": firmas, "tiene": tiene,
        "falta": [e for e in falta_req] + [f"Firma de {e}" for e in firmas_faltan],
        "sin_registro": sin_registro, "completos": completos, "total": total,
        "listo": completos == total, "listo_hoja": si_no(req.get("listo")),
        "siguiente": siguiente, "pasos": pasos, "firmas_faltan": firmas_faltan, "falta_req": falta_req,
    }
