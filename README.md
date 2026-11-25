# TechMth_Solutions
## Automatización para la Coordinación de Titulación · TecNM Campus Matehuala

Sistema en Python que atiende a los egresados por WhatsApp, Telegram, correo (Gmail y Outlook) y llamadas:

Resuelve sus dudas sobre el proceso de titulación integral por residencia profesional.
Les dice qué ya tienen y qué les falta para titularse.
Les muestra la ruta para concluir su titulación, paso por paso.

» Portal de egresados (primera pantalla)
  1. El egresado escribe su número de control. Para probar, usa el de ejemplo 24660999.
  2. Si es nuevo, llena sus datos en el mismo orden que la tabla Alumno: Nº Control, Nombre Completo, Carrera, Correo Institucional,   Correo Personal y Teléfono.
  3. Los confirma en una vista igual a la tabla de Excel, y se guardan con ese formato.
  4. Si ya estaba registrado, puede entrar o actualizar sus datos.

  Al pie del portal está el Acceso Coordinación, protegido con contraseña. Solo sirve para descargar el Excel: la página nunca muestra los datos.

- Después de entrar
  * Inicio
  
  * Banner con el logo de TechMth Solutions.
  
  * Mi avance de titulación: barra de progreso, «Lo que ya tienes», «Lo que te falta» y la ruta para concluir su titulación.
  
  * Tarjetas de los canales de atención.
  
  * WhatsApp · Telegram · Correo · Llamadas: cada canal en su propia sección, con preguntas frecuentes de un toque. Las llamadas se contestan por texto.
  
  * Panel «Mi avance»: en computadora queda fijo a la derecha; en tableta y celular se desliza desde el borde cuando hace falta.

- Diseño skeuomórfico
  * Encabezado: textura de piel azul marino con filo de luz.

  * Superficies: tarjetas como hojas de papel con sombra real, y el área de conversación hundida en la página.

  * Botones y globos: botones con brillo y relieve que se levantan al pasar el mouse; globos de chat tipo vidrio.

  * Barra de progreso: con volumen.

  * Barra de navegación: solo con los íconos (Inicio, WhatsApp, Telegram, Correo y Llamadas) en mosaicos con relieve. El nombre aparece al pasar el mouse.

  * Logos institucionales: el TecNM y el Instituto Tecnológico de Matehuala van en una placa en el encabezado, el portal, el Inicio y el Acceso Coordinación.

```texto
  Tec/
├── .github/workflows/     ← publica la página (no se toca)
├── TechMth_Solutions/     ← la automatización (no se toca)
├── documentacion/         ← los PDF de E3 y E4
└── README.md
```
