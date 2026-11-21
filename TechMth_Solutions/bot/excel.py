"""Almacén de datos en un solo archivo de Excel, una hoja por tabla.

- Hojas de datos del alumno (las mismas de la Coordinación): Alumno, Requisitos, No Adeudo.
- Hojas que llena el bot: Mensajes, Llamadas, Pendientes.

Cada operación vuelve a leer el archivo del disco antes de escribir, para no borrar lo que
el personal haya capturado a mano. Si el archivo está abierto en Excel de escritorio
(Windows lo bloquea), las escrituras esperan en una cola y se reintentan solas.
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .texto import normalizar, normalizar_encabezado, normalizar_telefono

AZUL = "000B3D"
TURQUESA = "2A9BAE"
CREMA = "F5F2EA"

# hoja → [(clave interna, encabezado visible, ancho)]
HOJAS: dict[str, list[tuple[str, str, int]]] = {
    "Alumno": [("num_control", "Nº Control", 13), ("nombre", "Nombre Completo", 34),
               ("carrera", "Carrera", 10), ("correo_institucional", "Correo Institucional", 32),
               ("correo_personal", "Correo Personal", 30), ("telefono", "Teléfono", 16)],
    "Requisitos": [("num_control", "Nº Control", 13), ("nombre", "Nombre del Estudiante", 34),
                   ("creditos", "Créditos", 11), ("servicio_social", "Servicio Social", 15),
                   ("ingles", "Inglés Acreditado", 17), ("listo", "Listo para Titular", 18)],
    "No Adeudo": [("num_control", "Nº Control", 13), ("nombre", "Nombre del Estudiante", 34),
                  ("recursos_financieros", "Recursos Financieros", 20),
                  ("coordinador", "Coordinador", 14), ("biblioteca", "Biblioteca", 12),
                  ("centro_informacion", "Centro de Información", 21), ("almacen", "Almacén", 10)],
    "Mensajes": [("fecha", "Fecha", 17), ("canal", "Canal", 11), ("remitente", "Remitente", 28),
                 ("nombre", "Nombre", 26), ("num_control", "Nº Control", 13),
                 ("asunto", "Asunto", 24), ("mensaje", "Mensaje", 50), ("intencion", "Intención", 16),
                 ("respuesta", "Respuesta", 60), ("atendido_por", "Atendido por", 14)],
    "Llamadas": [("fecha", "Fecha", 17), ("numero", "Número", 16), ("num_control", "Nº Control", 13),
                 ("nombre", "Nombre", 26), ("duracion", "Duración (s)", 13),
                 ("lo_que_dijo", "Lo que dijo", 45), ("respuesta", "Respuesta enviada", 60),
                 ("enviada_por", "Enviada por", 13)],
    "Pendientes": [("fecha", "Fecha", 17), ("canal", "Canal", 11), ("remitente", "Remitente", 28),
                   ("num_control", "Nº Control", 13), ("mensaje", "Mensaje", 50),
                   ("motivo", "Motivo", 34), ("estado", "Estado", 12)],
}

# Encabezados alternativos que se aceptan en un Excel ya existente
ALIAS = {
    "no control": "num_control", "n control": "num_control", "numero de control": "num_control",
    "num control": "num_control", "control": "num_control", "matricula": "num_control",
    "no de control": "num_control",
    "nombre completo": "nombre", "nombre del estudiante": "nombre", "nombre": "nombre",
    "nombre del alumno": "nombre", "alumno": "nombre",
    "carrera": "carrera", "correo institucional": "correo_institucional",
    "correo personal": "correo_personal", "telefono": "telefono", "celular": "telefono",
    "creditos": "creditos", "creditos complementarios": "creditos",
    "servicio social": "servicio_social", "ingles acreditado": "ingles", "ingles": "ingles",
    "listo para titular": "listo", "listo para titularse": "listo",
    "recursos financieros": "recursos_financieros", "coordinador": "coordinador",
    "coordinacion": "coordinador", "coordinacion de carrera": "coordinador",
    "biblioteca": "biblioteca", "centro de informacion": "centro_informacion",
    "almacen": "almacen",
}


def _clave(encabezado) -> str | None:
    n = normalizar_encabezado(encabezado)
    if not n:
        return None
    if n in ALIAS:
        return ALIAS[n]
    for hoja in HOJAS.values():
        for clave, visible, _ in hoja:
            if normalizar_encabezado(visible) == n:
                return clave
    return n.replace(" ", "_")


class ArchivoOcupado(Exception):
    pass


class AlmacenExcel:
    def __init__(self, ruta: str | Path, reintento_segundos: int = 20):
        self.ruta = Path(ruta).expanduser()
        self._candado = threading.RLock()
        self._cola: list[tuple[str, tuple, dict]] = []
        self._reintento = reintento_segundos
        self._hilo: threading.Thread | None = None
        self.al_guardar: list = []   # funciones a llamar después de cada guardado (p. ej. respaldo)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta.exists():
            self.crear_plantilla()
        else:
            self._respaldo_diario()
            self._asegurar_hojas()

    # ------------------------------------------------------------- archivo
    def crear_plantilla(self):
        wb = Workbook()
        wb.remove(wb.active)
        for nombre in HOJAS:
            ws = wb.create_sheet(nombre)
            self._preparar_hoja(ws, nombre)
        self._guardar(wb)

    def _preparar_hoja(self, ws, nombre: str):
        columnas = HOJAS[nombre]
        for i, (_, visible, ancho) in enumerate(columnas, start=1):
            celda = ws.cell(row=1, column=i, value=visible)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor=AZUL)
            celda.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(i)].width = ancho
        ws.freeze_panes = "A2"
        ref = f"A1:{get_column_letter(len(columnas))}2"
        tabla = Table(displayName="Tabla" + nombre.replace(" ", ""), ref=ref)
        tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(tabla)

    def _asegurar_hojas(self):
        """Agrega las hojas que falten (por ejemplo Mensajes en un Excel que ya existía)
        y la columna Nº Control donde no exista."""
        with self._candado:
            wb = self._abrir()
            cambios = False
            for nombre, columnas in HOJAS.items():
                ws = self._hoja(wb, nombre)
                if ws is None:
                    ws = wb.create_sheet(nombre)
                    self._preparar_hoja(ws, nombre)
                    cambios = True
                    continue
                fila_enc, mapa = self._encabezados(ws)
                for clave, visible, ancho in columnas:
                    if clave in ("num_control", "nombre") and clave not in mapa.values():
                        col = ws.max_column + 1
                        celda = ws.cell(row=fila_enc, column=col, value=visible)
                        celda.font = Font(bold=True, color="FFFFFF")
                        celda.fill = PatternFill("solid", fgColor=AZUL)
                        ws.column_dimensions[get_column_letter(col)].width = ancho
                        self._extender_tablas(ws, columnas=col)
                        mapa[col] = clave
                        cambios = True
            if cambios:
                try:
                    self._guardar(wb)
                except ArchivoOcupado:
                    pass

    def _respaldo_diario(self):
        destino = self.ruta.with_name(f"{self.ruta.stem}_respaldo_{date.today():%Y%m%d}{self.ruta.suffix}")
        if not destino.exists():
            try:
                shutil.copy2(self.ruta, destino)
            except OSError:
                pass

    def _abrir(self):
        return load_workbook(self.ruta)

    def _guardar(self, wb):
        temporal = self.ruta.with_name(f"~tmp_{os.getpid()}_{self.ruta.name}")
        try:
            wb.save(temporal)
            os.replace(temporal, self.ruta)
        except PermissionError as e:
            temporal.unlink(missing_ok=True)
            raise ArchivoOcupado(str(e)) from e

    @staticmethod
    def _hoja(wb, nombre: str):
        buscado = normalizar(nombre)
        for ws in wb.worksheets:
            if normalizar(ws.title) == buscado:
                return ws
        return None

    @staticmethod
    def _encabezados(ws) -> tuple[int, dict[int, str]]:
        """Fila de encabezados (la primera con 2+ columnas reconocidas) y columna→clave."""
        conocidas = {c for cols in HOJAS.values() for c, _, _ in cols}
        for fila in range(1, min(ws.max_row, 10) + 1):
            mapa = {}
            for col in range(1, ws.max_column + 1):
                clave = _clave(ws.cell(row=fila, column=col).value)
                if clave:
                    mapa[col] = clave
            if sum(1 for c in mapa.values() if c in conocidas) >= 2:
                return fila, mapa
        return 1, {}

    @staticmethod
    def _extender_tablas(ws, fila: int | None = None, columnas: int | None = None):
        for tabla in ws.tables.values():
            inicio, fin = tabla.ref.split(":")
            col_ini = "".join(c for c in inicio if c.isalpha())
            fila_ini = int("".join(c for c in inicio if c.isdigit()))
            col_fin = "".join(c for c in fin if c.isalpha())
            fila_fin = int("".join(c for c in fin if c.isdigit()))
            if fila and fila > fila_fin:
                fila_fin = fila
            if columnas:
                col_fin = get_column_letter(max(columnas, ws[f"{col_fin}1"].column))
            nueva = f"{col_ini}{fila_ini}:{col_fin}{fila_fin}"
            if nueva != tabla.ref:
                tabla.ref = nueva
                if tabla.autoFilter is not None:
                    tabla.autoFilter.ref = nueva
                if columnas and tabla.tableColumns:
                    # el Excel exige un nombre por columna de la tabla
                    from openpyxl.worksheet.table import TableColumn
                    existentes = len(tabla.tableColumns)
                    for i in range(existentes, columnas - ws[f"{col_ini}1"].column + 1):
                        nombre = ws.cell(row=fila_ini, column=ws[f"{col_ini}1"].column + i).value
                        tabla.tableColumns.append(TableColumn(id=i + 1, name=str(nombre or f"Columna{i + 1}")))

    @staticmethod
    def _fila_vacia(ws, fila: int, columnas) -> bool:
        return all(ws.cell(row=fila, column=c).value in (None, "") for c in columnas)

    # ----------------------------------------------------------- lectura
    def filas(self, hoja: str) -> list[dict]:
        with self._candado:
            wb = load_workbook(self.ruta, read_only=False, data_only=True)
            ws = self._hoja(wb, hoja)
            if ws is None:
                return []
            fila_enc, mapa = self._encabezados(ws)
            res = []
            for fila in range(fila_enc + 1, ws.max_row + 1):
                datos = {clave: ws.cell(row=fila, column=col).value for col, clave in mapa.items()}
                if any(v not in (None, "") for v in datos.values()):
                    datos["_fila"] = fila
                    res.append(datos)
            return res

    def todas(self) -> dict[str, list[dict]]:
        """Todas las hojas conocidas, leyendo el archivo una sola vez (para mostrarlas)."""
        with self._candado:
            wb = load_workbook(self.ruta, data_only=True)
            res = {}
            for hoja in HOJAS:
                ws = self._hoja(wb, hoja)
                filas = []
                if ws is not None:
                    fila_enc, mapa = self._encabezados(ws)
                    for fila in range(fila_enc + 1, ws.max_row + 1):
                        datos = {c: ws.cell(row=fila, column=col).value for col, c in mapa.items()}
                        if any(v not in (None, "") for v in datos.values()):
                            filas.append(datos)
                res[hoja] = filas
            return res

    def buscar(self, hoja: str, clave: str, valor) -> dict | None:
        buscado = self._comparable(clave, valor)
        if not buscado:
            return None
        for fila in self.filas(hoja):
            if self._comparable(clave, fila.get(clave)) == buscado:
                return fila
        return None

    @staticmethod
    def _comparable(clave: str, valor) -> str:
        if valor is None:
            return ""
        if clave == "telefono":
            return normalizar_telefono(valor) or ""
        texto = str(valor).strip()
        if clave == "num_control":
            if isinstance(valor, float) and valor.is_integer():
                texto = str(int(valor))
            texto = "".join(c for c in texto if c.isdigit())
        return texto.lower()

    def buscar_alumno_por_contacto(self, telefono: str | None = None, correo: str | None = None):
        tel = normalizar_telefono(telefono) if telefono else None
        correo = (correo or "").lower().strip()
        for fila in self.filas("Alumno"):
            if tel and normalizar_telefono(fila.get("telefono")) == tel:
                return fila
            if correo and correo in {str(fila.get("correo_institucional") or "").lower().strip(),
                                     str(fila.get("correo_personal") or "").lower().strip()}:
                return fila
        return None

    # ---------------------------------------------------------- escritura
    def agregar(self, hoja: str, datos: dict) -> bool:
        return self._escribir("agregar", (hoja, datos))

    def actualizar(self, hoja: str, clave: str, valor, datos: dict, crear: bool = True) -> bool:
        """Actualiza la fila cuyo `clave` = `valor`; si no existe y crear=True, la agrega."""
        return self._escribir("actualizar", (hoja, clave, valor, datos, crear))

    def _escribir(self, operacion: str, args: tuple) -> bool:
        with self._candado:
            self._cola.append((operacion, args, {}))
            return self._vaciar_cola()

    def _vaciar_cola(self) -> bool:
        if not self._cola:
            return True
        try:
            wb = self._abrir()
        except PermissionError:
            self._programar_reintento()
            return False
        for operacion, args, _ in self._cola:
            getattr(self, f"_op_{operacion}")(wb, *args)
        try:
            self._guardar(wb)
        except ArchivoOcupado:
            self._programar_reintento()
            return False
        self._cola.clear()
        for funcion in self.al_guardar:
            try:
                funcion()
            except Exception:  # noqa: BLE001 - un respaldo fallido no detiene el registro
                pass
        return True

    @property
    def pendientes_de_guardar(self) -> int:
        return len(self._cola)

    def _programar_reintento(self):
        if self._hilo and self._hilo.is_alive():
            return
        if sys.platform == "emscripten":  # en el navegador no hay hilos
            return

        def reintentar():
            while True:
                time.sleep(self._reintento)
                with self._candado:
                    if self._vaciar_cola():
                        return

        self._hilo = threading.Thread(target=reintentar, daemon=True)
        self._hilo.start()

    def cerrar(self) -> Path | None:
        """Al salir: si el Excel siguió ocupado, guarda lo pendiente en otro Excel."""
        with self._candado:
            if self._vaciar_cola():
                return None
            destino = self.ruta.with_name(f"{self.ruta.stem}_pendientes_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
            wb = Workbook()
            wb.remove(wb.active)
            for nombre in HOJAS:
                self._preparar_hoja(wb.create_sheet(nombre), nombre)
            for operacion, args, _ in self._cola:
                if operacion == "agregar":
                    self._op_agregar(wb, *args)
                else:
                    self._op_actualizar(wb, *args)
            wb.save(destino)
            self._cola.clear()
            return destino

    # -------------------------------------------------- operaciones en libro
    def _op_agregar(self, wb, hoja: str, datos: dict):
        ws = self._hoja(wb, hoja)
        if ws is None:
            ws = wb.create_sheet(hoja)
            self._preparar_hoja(ws, hoja)
        fila_enc, mapa = self._encabezados(ws)
        cols = list(mapa)
        fila = None
        # primero, filas vacías dentro de la tabla (como la fila 2 de una tabla nueva)
        limite = ws.max_row
        for tabla in ws.tables.values():
            limite = max(limite, int("".join(c for c in tabla.ref.split(":")[1] if c.isdigit())))
        for f in range(fila_enc + 1, limite + 1):
            if self._fila_vacia(ws, f, cols):
                fila = f
                break
        if fila is None:
            fila = limite + 1
        self._poner(ws, fila, mapa, datos)
        self._extender_tablas(ws, fila=fila)

    def _op_actualizar(self, wb, hoja, clave, valor, datos, crear):
        ws = self._hoja(wb, hoja)
        if ws is not None:
            fila_enc, mapa = self._encabezados(ws)
            col = next((c for c, k in mapa.items() if k == clave), None)
            buscado = self._comparable(clave, valor)
            if col:
                for f in range(fila_enc + 1, ws.max_row + 1):
                    if self._comparable(clave, ws.cell(row=f, column=col).value) == buscado:
                        self._poner(ws, f, mapa, datos)
                        return
        if crear:
            self._op_agregar(wb, hoja, {clave: valor, **datos})

    @staticmethod
    def _poner(ws, fila: int, mapa: dict[int, str], datos: dict):
        for col, clave in mapa.items():
            if clave not in datos:
                continue
            valor = datos[clave]
            celda = ws.cell(row=fila, column=col)
            if clave == "num_control" and valor not in (None, "") and str(valor).isdigit():
                valor = int(valor)  # igual que en la hoja de la Coordinación
            celda.value = valor
            if isinstance(valor, datetime):
                celda.number_format = "dd/mm/yyyy hh:mm"
            if clave in ("mensaje", "respuesta", "lo_que_dijo"):
                celda.alignment = Alignment(wrap_text=True, vertical="top")
