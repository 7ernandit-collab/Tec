"""Entiende la intención del mensaje con reglas locales (sin internet ni IA externa).

Cada intención tiene frases con peso. Se suman los pesos de las frases que aparecen en el
mensaje; las palabras largas también cuentan si están mal escritas (coincidencia aproximada).
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .texto import normalizar

UMBRAL = 2.0          # puntaje mínimo para aceptar una intención
UMBRAL_SECUNDARIA = 3.0
SIMILITUD = 0.84      # para palabras con faltas de ortografía
SOCIALES = {"saludo", "despedida", "gracias"}


@dataclass
class Resultado:
    principal: str | None
    secundarias: list[str]
    saludo: bool
    despedida: bool
    gracias: bool
    puntajes: dict[str, float]


class Clasificador:
    def __init__(self, intenciones: dict, menu: list):
        self.intenciones = {nombre: {normalizar(k): float(v) for k, v in datos["palabras"].items()}
                            for nombre, datos in intenciones.items()}
        self.menu = {num: intencion for num, intencion, _ in menu}

    @staticmethod
    def _parecida(palabra: str, tokens: list[str]) -> bool:
        if len(palabra) < 5:
            return False
        return any(abs(len(t) - len(palabra)) <= 2 and
                   SequenceMatcher(None, palabra, t).ratio() >= SIMILITUD for t in tokens)

    def puntuar(self, texto: str) -> dict[str, float]:
        norm = normalizar(texto)
        tokens = norm.split()
        conjunto = set(tokens)
        relleno = f" {norm} "
        puntajes: dict[str, float] = {}
        for nombre, frases in self.intenciones.items():
            total = 0.0
            for frase, peso in frases.items():
                if " " in frase:
                    if f" {frase} " in relleno:
                        total += peso
                elif frase in conjunto:
                    total += peso
                elif self._parecida(frase, tokens):
                    total += peso * 0.8
            if total:
                puntajes[nombre] = total
        return puntajes

    def clasificar(self, texto: str) -> Resultado:
        norm = normalizar(texto)
        if norm in self.menu:  # respuesta con número del menú
            return Resultado(self.menu[norm], [], False, False, False, {self.menu[norm]: 99})
        puntajes = self.puntuar(texto)
        sociales = {k: puntajes.get(k, 0) >= 1 for k in SOCIALES}
        temas = sorted(((v, k) for k, v in puntajes.items() if k not in SOCIALES and v >= UMBRAL),
                       reverse=True)
        principal = temas[0][1] if temas else None
        secundarias = [k for v, k in temas[1:3] if v >= UMBRAL_SECUNDARIA]
        return Resultado(principal, secundarias, sociales["saludo"], sociales["despedida"],
                         sociales["gracias"], puntajes)
