# Convenciones

## Python Y UI

- Mantener la GUI en el hilo principal; las operaciones HTTP, SQLite costosas y
  vistas previas se ejecutan mediante `QThread` y senales.
- Usar nombres explicitos para opciones, estadisticas y contexto de descarga.
- No actualizar widgets desde un worker.
- Los mensajes al usuario no deben incluir tokens, claves ni respuestas HTTP
  completas que puedan contener datos personales.

## HTTP Y Errores

- Usar exclusivamente `SgdApiClient` para la API SGD.
- Enviar el token como `Authorization: Bearer`; no persistirlo.
- Reintentar solo respuestas `429` con espera acotada. Los demas errores se
  propagan como `SgdApiError` y se registran de forma resumida.
- No usar rutas historicas del SGD fuera de `/api/cargos`.

## Persistencia Y Archivos

- Toda lectura o escritura local se delimita por periodo, alcance y `depe_id`.
- Los documentos principales son la base de la vista previa y del Excel; los
  relacionados se representan mediante `document_relations`.
- Los nombres de archivo se sanitizan para Windows y los adjuntos relacionados
  se prefijan para evitar colisiones dentro de la carpeta principal.
- Un archivo existente es valido si el SGD no informo tamano o si coincide con
  `file_size`.

## Documentacion

- Cada tema tiene una fuente normativa indicada en [guia_IA.md](guia_IA.md).
- No copiar contratos de tablas o endpoints en varios documentos; enlazar la
  fuente aplicable.
- Actualizar la memoria cuando cambien permisos, flujo, esquema, contrato
  externo, configuracion o reglas propias de la capa.
