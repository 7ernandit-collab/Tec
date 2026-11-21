"""Pruebas de la automatización de TechMth Solutions. Ejecutar:  python -m unittest discover pruebas"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from openpyxl import Workbook, load_workbook  # noqa: E402
from openpyxl.worksheet.table import Table  # noqa: E402

from bot.canales import MensajeEntrante as M  # noqa: E402
from bot.ejemplo import cargar_ejemplo  # noqa: E402
from bot.excel import AlmacenExcel  # noqa: E402
from bot.motor import Bot  # noqa: E402
from bot.texto import extraer_num_control, extraer_telefono  # noqa: E402

TEL_DEMO = "488 000 1234"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.excel = AlmacenExcel(self.tmp / "bot.xlsx")
        cargar_ejemplo(self.excel)
        self.bot = Bot(self.excel, RAIZ / "base_conocimiento.json", semilla=7)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wa(self, texto, tel=TEL_DEMO, **kw):
        return self.bot.procesar(M("whatsapp", tel, texto, **kw))


class Entendimiento(Base):
    def test_preguntas_naturales(self):
        casos = {
            "q papeles ocupo para el expediente": "documentos",
            "cuanto cuesta titularse?": "pago",
            "cuando seria mi acto protocolario": "acto",
            "que firmas necesito para la carta de no adeudo": "no_adeudo",
            "y si repruebo el acto?": "reprobar",
            "cuanto tarda todo el tramite": "duracion",
            "necesito el ingles acreditado?": "ingles",
            "donde esta la oficina de la coordinacion": "contacto",
            "requisistos para titularme": "requisitos",   # con falta de ortografía
            "3": "no_adeudo",                              # opción del menú
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(self.bot.nlu.clasificar(texto).principal, esperado)

    def test_dos_preguntas_en_un_mensaje(self):
        r = self.wa("cuanto cuesta y cuando es el acto?")
        self.assertIn("referencia", r.texto)
        self.assertIn("3 días hábiles", r.texto)

    def test_no_entiende_y_deja_pendiente(self):
        r = self.wa("asdfgh qwerty", tel="4440000000")
        self.assertEqual(r.atendido_por, "Pendiente")
        self.assertEqual(self.excel.filas("Pendientes")[-1]["motivo"], "El bot no entendió la pregunta")

    def test_entidades(self):
        self.assertEqual(extraer_num_control("mi control es L24660999"), "24660999")
        self.assertIsNone(extraer_num_control("mi cel 4880001234"))
        self.assertEqual(extraer_telefono("cel: +52 (488) 000-1234"), "4880001234")


class Estatus(Base):
    def test_estatus_reconoce_por_telefono(self):
        r = self.wa("como va mi tramite?")
        self.assertIn("Falta: Coordinador y Biblioteca", r.texto)
        self.assertIn("Valeria", r.texto)

    def test_estatus_bloqueado_desde_otro_contacto(self):
        r = self.bot.procesar(M("outlook", "extrano@outlook.com", "estatus 24660999"))
        self.assertIn("Por seguridad", r.texto)
        self.assertNotIn("Biblioteca", r.texto)

    def test_estatus_por_correo_registrado(self):
        r = self.bot.procesar(M("gmail", "valeria.demo@gmail.com", "¿qué me falta?", asunto="Duda"))
        self.assertTrue(r.asunto.startswith("Re:"))
        self.assertIn("Biblioteca", r.texto)
        self.assertNotIn("*", r.texto)  # sin formato de WhatsApp en correos


class Registro(Base):
    def test_registro_completo_guarda_en_tres_hojas(self):
        tel = "4441112233"
        for t in ["quiero registrarme", "24660150", "Pedro Ruiz Gómez", "sistemas", "si",
                  "omitir", "si"]:
            r = self.wa(t, tel=tel)
        self.assertIn("quedaron registrados", r.texto)
        alumno = self.excel.buscar("Alumno", "num_control", "24660150")
        self.assertEqual(alumno["nombre"], "Pedro Ruiz Gómez")
        self.assertEqual(alumno["carrera"], "ISC")
        self.assertEqual(alumno["telefono"], "444 111 2233")       # tomado de WhatsApp
        self.assertEqual(alumno["correo_institucional"], "L24660150@matehuala.tecnm.mx")
        self.assertIsNotNone(self.excel.buscar("Requisitos", "num_control", "24660150"))
        self.assertIsNotNone(self.excel.buscar("No Adeudo", "num_control", "24660150"))

    def test_no_sobrescribe_registro_ajeno(self):
        tel = "4449998877"
        for t in ["registrarme", "24660999", "Otra Persona", "ISC", "si", "omitir", "si"]:
            r = self.wa(t, tel=tel)
        self.assertEqual(r.atendido_por, "Pendiente")
        self.assertEqual(self.excel.buscar("Alumno", "num_control", "24660999")["telefono"], TEL_DEMO)

    def test_actualizar_correo(self):
        self.wa("quiero cambiar mi correo personal")
        self.wa("ana.nueva@gmail.com")
        self.assertEqual(self.excel.buscar("Alumno", "num_control", "24660999")["correo_personal"],
                         "ana.nueva@gmail.com")

    def test_cancelar_flujo(self):
        self.wa("registrarme", tel="4441110000")
        r = self.wa("cancelar", tel="4441110000")
        self.assertIn("Listo, lo dejamos", r.texto)


class Canales(Base):
    def test_llamada_se_responde_por_texto_y_se_guarda(self):
        r = self.bot.procesar(M("llamada", "4447776655", "", duracion=0))
        self.assertEqual(r.canal, "whatsapp")
        self.assertIn("Recibimos tu llamada", r.texto)
        r = self.bot.procesar(M("llamada", "4447776655", "cuales son los requisitos", duracion=35))
        self.assertIn("sobre tu llamada", r.texto)
        filas = self.excel.filas("Llamadas")
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[-1]["duracion"], 35)

    def test_telegram(self):
        r = self.bot.procesar(M("telegram", TEL_DEMO, "¿qué me falta?"))
        self.assertEqual(r.canal, "telegram")
        self.assertIn("Biblioteca", r.texto)                    # reconoce a la egresada por su teléfono
        r = self.bot.procesar(M("telegram", "@alguien", "estatus 24660999"))
        self.assertIn("Por seguridad", r.texto)                 # un @usuario desconocido no ve datos
        self.assertEqual(self.excel.filas("Mensajes")[-1]["canal"], "Telegram")

    def test_correo_quita_historial(self):
        cuerpo = "¿Qué documentos lleva?\n\nEl lun 18 escribió:\n> pago pago pago"
        r = self.bot.procesar(M("gmail", "x@gmail.com", cuerpo))
        self.assertEqual(r.intencion, "documentos")

    def test_humano_deja_pendiente(self):
        self.wa("quiero hablar con una persona", tel="4440001111")
        r = self.wa("No me llegó mi referencia de pago", tel="4440001111")
        self.assertEqual(r.atendido_por, "Pendiente")
        self.assertEqual(self.excel.filas("Pendientes")[-1]["motivo"], "Solicita atención de una persona")

    def test_todo_mensaje_queda_en_excel(self):
        self.wa("hola")
        self.bot.procesar(M("outlook", "a@outlook.com", "requisitos"))
        self.assertEqual(len(self.excel.filas("Mensajes")), 2)


class PortalRegistro(Base):
    def test_numero_de_control(self):
        from bot import registro
        self.assertEqual(registro.leer_num_control("L24660999"), "24660999")
        self.assertIsNone(registro.leer_num_control("2466014"))
        self.assertIsNone(registro.leer_num_control("hola"))

    def test_valida_y_guarda_con_formato_de_la_tabla(self):
        from bot import registro
        datos = {"nombre": "maría josé pérez", "carrera": "IIND · Ingeniería Industrial",
                 "correo_institucional": "l24660177@MATEHUALA.tecnm.mx", "correo_personal": "",
                 "telefono": "+52 (488) 111-2233"}
        limpios, errores = registro.validar(datos, nuevo=True)
        self.assertEqual(errores, {})
        registro.guardar(self.excel, "24660177", limpios, nuevo=True)
        fila = self.excel.buscar("Alumno", "num_control", "24660177")
        self.assertEqual([fila[k] for k, _ in registro.CAMPOS],
                         [24660177, "María José Pérez", "IIND", "L24660177@matehuala.tecnm.mx", None, "488 111 2233"])
        self.assertIsNotNone(self.excel.buscar("No Adeudo", "num_control", "24660177"))

    def test_errores_y_actualizacion_parcial(self):
        from bot import registro
        _, errores = registro.validar({"nombre": "Val", "carrera": "XYZ", "correo_institucional": "a@gmail.com",
                                       "telefono": "123"}, nuevo=True)
        self.assertEqual(set(errores), {"nombre", "carrera", "correo_institucional", "telefono"})
        limpios, errores = registro.validar({"telefono": "4889990000"}, nuevo=False)
        registro.guardar(self.excel, "24660999", limpios, nuevo=False)
        fila = self.excel.buscar("Alumno", "num_control", "24660999")
        self.assertEqual(fila["telefono"], "488 999 0000")
        self.assertEqual(fila["correo_personal"], "valeria.demo@gmail.com")  # lo demás se conserva


class ExcelReal(unittest.TestCase):
    """Un archivo como el de la Coordinación: encabezado «Nº Comtrol», fila 2 vacía y
    hoja No Adeudo sin número de control."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ruta = self.tmp / "coordinacion.xlsx"
        wb = Workbook()
        wb.remove(wb.active)
        ws = wb.create_sheet("Alumno")
        ws.append(["Nº Comtrol", "Nombre Completo", "Carrera", "Correo Institucional",
                   "Correo Personal", "Teléfono"])
        ws.append([None] * 6)
        ws.append([24660999, "Valeria Torres Ruiz", "ISC", "L24660999@matehuala.tecnm.mx",
                   "valeria.demo@gmail.com", "488 000 1234"])
        ws.add_table(Table(displayName="Tabla1", ref="A1:F3"))
        ws = wb.create_sheet("No Adeudo")
        ws.append(["Recursos Financieros", "Coordinador", "Biblioteca", "Centro de Información", "Almacén"])
        ws.append(["Si", "No", "No", "Si", "Si"])
        ws.add_table(Table(displayName="Tabla3", ref="A1:E2"))
        wb.save(self.ruta)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_respeta_y_completa_el_archivo(self):
        a = AlmacenExcel(self.ruta)
        self.assertEqual(a.buscar("Alumno", "num_control", "24660999")["telefono"], "488 000 1234")
        a.agregar("Alumno", {"num_control": "24660150", "nombre": "Nuevo Alumno"})
        wb = load_workbook(self.ruta)
        self.assertEqual(wb["Alumno"]["A2"].value, 24660150)          # usó la fila vacía
        self.assertIn("Nº Control", [c.value for c in wb["No Adeudo"][1]])  # agregó la columna
        self.assertEqual(wb["No Adeudo"].tables["Tabla3"].ref, "A1:G2")
        for hoja in ("Mensajes", "Llamadas", "Pendientes", "Requisitos"):
            self.assertIn(hoja, wb.sheetnames)
        self.assertTrue(any(p.name.startswith("coordinacion_respaldo_") for p in self.tmp.iterdir()))

    def test_archivo_abierto_espera_y_reintenta(self):
        a = AlmacenExcel(self.ruta, reintento_segundos=3600)
        original = a._guardar
        with mock.patch.object(a, "_guardar", side_effect=PermissionError("abierto en Excel")):
            with mock.patch.object(a, "_programar_reintento"):
                a._guardar.side_effect = __import__("bot.excel", fromlist=["ArchivoOcupado"]).ArchivoOcupado("x")
                self.assertFalse(a.agregar("Mensajes", {"mensaje": "hola"}))
                self.assertEqual(a.pendientes_de_guardar, 1)
        a._guardar = original
        self.assertTrue(a.agregar("Mensajes", {"mensaje": "segundo"}))
        self.assertEqual([f["mensaje"] for f in a.filas("Mensajes")], ["hola", "segundo"])


if __name__ == "__main__":
    unittest.main()


class Respaldo(unittest.TestCase):
    def test_sube_y_descarga_con_api_de_github(self):
        import base64
        from bot.respaldo_github import RespaldoGitHub
        tmp = Path(tempfile.mkdtemp())
        ruta = tmp / "x.xlsx"
        ruta.write_bytes(b"EXCEL-1")
        r = RespaldoGitHub("token", "usuario/datos", ruta)
        llamadas = []

        def falso(metodo, url, cuerpo=None, crudo=False):
            llamadas.append((metodo, crudo, cuerpo))
            if metodo == "GET" and crudo:
                return b"EXCEL-REMOTO"
            if metodo == "GET":
                return {"sha": "abc"}
            return {}
        r._pedir = falso
        self.assertTrue(r.subir())
        put = [c for c in llamadas if c[0] == "PUT"][0][2]
        self.assertEqual(base64.b64decode(put["content"]), b"EXCEL-1")
        self.assertEqual(put["sha"], "abc")
        self.assertTrue(r.descargar())
        self.assertEqual(ruta.read_bytes(), b"EXCEL-REMOTO")
        shutil.rmtree(tmp, ignore_errors=True)
