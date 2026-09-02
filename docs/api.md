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
- Los relacionados se consultan por lotes de IDs, paginados. Cada fila debe
  incluir `master_id`; `meta.related_total` representa el total del lote y no
  solo la pagina.
- La descarga de un relacionado incluye `master_id` para que el SGD valide el
  acceso al principal.
- El cliente reintenta unicamente `429`. Un `404` al descargar puede indicar que
  el archivo no esta disponible en el storage del backend.

El detalle de los campos remotos no se duplica aqui porque el contrato fuente
vive en el SGD. La representacion local y sus relaciones estan documentadas en
[modelo-datos.md](modelo-datos.md).
