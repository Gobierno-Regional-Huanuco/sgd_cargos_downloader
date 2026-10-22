# Contrato HTTP Externo Consumido

## Alcance

La aplicacion no expone endpoints HTTP. Este documento registra el contrato
externo del SGD que consume `SgdApiClient`; la autoridad de rutas, permisos,
payloads y almacenamiento remoto pertenece al backend SGD.

La URL base proviene de `sgd_service.json`. El cliente usa JSON, `Accept:
application/json` y `Authorization: Bearer` despues del login. No se conserva
el token en disco.

## Operaciones Consumidas

| Metodo | Ruta | Acceso | Tipo | Propietario | Proposito |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/cargos/login` | Credenciales | accion | SGD | Obtener token temporal y datos del usuario |
| POST | `/api/cargos/logout` | Bearer | accion | SGD | Revocar el token actual |
| GET | `/api/cargos/me` | Bearer | proyeccion | SGD | Consultar identidad y permisos |
| GET | `/api/cargos/oficinas` | Bearer | proyeccion | SGD | Listar oficinas autorizadas |
| GET | `/api/cargos/documentos` | Bearer | consulta | SGD | Listar documentos del contexto paginado |
| POST | `/api/cargos/documentos/relacionados/batch` | Bearer | consulta | SGD | Obtener relacionados de un lote de principales |
| GET | `/api/cargos/archivos/{file_id}/download` | Bearer | consulta | SGD | Descargar un adjunto autorizado por streaming |

La aplicacion no es autoridad canonica de ninguna de estas rutas y no emite
mutaciones de documentos. Login y logout son acciones porque no representan un
recurso local gestionado por esta aplicacion.

## Reglas De Consumo

- Los documentos se consultan por periodo mediante `fecha_desde` y
  `fecha_hasta`, con `include_files=1`.
- Cada documento puede incluir `oficinas_destinatarias`, texto ya consolidado
  por el SGD con las oficinas derivadas directamente desde la operacion inicial
  de registro, sin incluir derivaciones posteriores, sin duplicados y ordenadas
  alfabeticamente. Puede ser `null` o no estar presente durante la compatibilidad
  con versiones anteriores; ambos casos representan una celda vacia y no
  excluyen el documento.
- Cada documento puede incluir `cui_proyecto`, `tipo_tramite` y
  `tipo_tramite_descripcion`. Los tres campos son opcionales durante la
  compatibilidad con versiones anteriores. El reporte muestra `cui_proyecto`
  como CUI y `tipo_tramite_descripcion` como Tipo de trámite; `tipo_tramite` se
  conserva solo como identificador interno. Valores nulos, vacios o ausentes
  dejan la celda correspondiente vacia y no excluyen el documento; un CUI cero
  tampoco se presenta.
- La separacion de reportes de oficina usa `docu_origen`, `docu_tipo` y
  `docu_idusuario`. Un origen `1` con tipo `0` identifica un documento de
  oficina; un origen `1` con tipo `1`, uno personal; los origenes `2` y `3`
  corresponden a documentos manuales/externos e interoperabilidad/PIDE. Los
  documentos con origen `1` y `docu_tipo` explicitamente `null` se consideran
  de oficina porque `0` es el valor predeterminado de ese campo; un campo
  ausente, vacio o invalido no activa este respaldo. Los
  personales se agrupan por `docu_idusuario`; mientras el backend actualizado se
  despliega, el consumidor usa temporalmente `oper_idusuario` solo cuando
  `docu_idusuario` esta ausente o es `null`. `docu_firma` solo aporta el nombre
  visible. Si no puede determinarse la clasificacion o faltan ambos IDs en un
  documento personal, el consumidor detiene la exportacion para evitar mezclas.
- Los documentos principales y relacionados incluyen `docu_numero_doc`,
  `docu_fecha_doc`, `docu_siglas_doc` y `tdoc_descripcion`. El consumidor usa
  estos campos para presentar la numeracion compuesta; `docu_siglas_doc` puede
  ser nulo y, en ese caso, se conserva la numeracion correlativa sin inventar
  siglas.
- Los relacionados se consultan por lotes de IDs, paginados. Cada fila debe
  incluir `master_id`; `meta.related_total` representa el total del lote y no
  solo la pagina.
- Cuando el alcance oficina incluye documentos personales, el consumidor
  propaga `include_personal=1` al listado, al lote de relacionados y a la
  descarga de archivos para conservar el mismo contexto de autorizacion.
- La descarga de un relacionado incluye `master_id` para que el SGD valide el
  acceso al principal.
- El cliente reintenta unicamente `429`. Un `404` al descargar puede indicar que
  el archivo no esta disponible en el storage del backend.

El detalle de los campos remotos no se duplica aqui porque el contrato fuente
vive en el SGD. La representacion local y sus relaciones estan documentadas en
[modelo-datos.md](modelo-datos.md).
