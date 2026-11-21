"""Simulador en la terminal: escribe como si fueras el alumno en cada canal."""
from __future__ import annotations

from .canales import CANALES, CORREOS, MensajeEntrante
from .motor import Bot

AYUDA = """
Comandos del simulador:
  /whatsapp 4880001234      escribir por WhatsApp desde ese número
  /sms 4880001234           escribir por SMS
  /gmail correo@gmail.com   escribir un correo de Gmail
  /outlook correo@hotmail.com   escribir un correo de Outlook
  /asunto Texto del asunto  (solo correos)
  /llamada 4880001234 45    simular una llamada (número y segundos); después escribe
                            lo que dijo la persona o deja vacío si colgó sin hablar
  /excel                    cuántos registros hay en cada hoja
  /ayuda   /salir
Todo lo demás se envía como mensaje.
"""


def ejecutar(bot: Bot):
    canal, remitente, asunto = "whatsapp", "4880001234", ""
    print("TechMth Solutions · Coordinación de Titulación (simulador en terminal)")
    print(f"Excel: {bot.excel.ruta}")
    print(AYUDA)
    while True:
        etiqueta = f"{CANALES[canal]} {remitente}" + (f" · {asunto}" if canal in CORREOS and asunto else "")
        try:
            linea = input(f"\n[{etiqueta}] Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not linea:
            continue
        if linea.startswith("/"):
            partes = linea[1:].split(maxsplit=2)
            cmd = partes[0].lower()
            if cmd == "salir":
                break
            if cmd == "ayuda":
                print(AYUDA)
            elif cmd in ("whatsapp", "telegram", "sms", "gmail", "outlook") and len(partes) > 1:
                canal, remitente = cmd, partes[1]
            elif cmd == "asunto":
                asunto = linea[len("/asunto"):].strip()
            elif cmd == "llamada" and len(partes) > 1:
                segundos = int(partes[2]) if len(partes) > 2 and partes[2].isdigit() else 0
                try:
                    dijo = input("   Lo que dijo en la llamada (Enter si no habló): ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                r = bot.procesar(MensajeEntrante("llamada", partes[1], dijo, duracion=segundos))
                _mostrar(r)
            elif cmd == "excel":
                for hoja in ("Alumno", "Requisitos", "No Adeudo", "Mensajes", "Llamadas", "Pendientes"):
                    print(f"   {hoja}: {len(bot.excel.filas(hoja))} filas")
                if bot.excel.pendientes_de_guardar:
                    print(f"   ⚠ {bot.excel.pendientes_de_guardar} cambios esperan a que se cierre el Excel")
            else:
                print("Comando no reconocido. Escribe /ayuda")
            continue
        r = bot.procesar(MensajeEntrante(canal, remitente, linea, asunto=asunto))
        _mostrar(r)
    destino = bot.excel.cerrar()
    if destino:
        print(f"El Excel seguía abierto; lo pendiente se guardó en {destino}")


def _mostrar(r):
    encabezado = f"Bot → {CANALES[r.canal]} {r.para}" + (f" · {r.asunto}" if r.asunto else "")
    print(f"\n{encabezado}\n" + "\n".join("   " + l for l in r.texto.splitlines()))
