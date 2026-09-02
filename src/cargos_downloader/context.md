# Contexto: Cargos Downloader

## Proposito

Permitir que un usuario autorizado del SGD construya un registro local de sus
cargos personales o de oficina, exporte los principales a Excel y descargue sus
adjuntos de forma reanudable.

## Alcance Y Limites

- Incluye: autenticacion ante SGD, seleccion de oficina, periodo, alcance,
  principales, relacionados, Excel y archivos locales.
- No incluye: modificar documentos, permisos o archivos dentro del SGD.
- Dependencias: API externa del SGD, PySide6, SQLite y sistema de archivos local.

## Actores Y Permisos

| Actor | Puede | No puede | Evidencia |
| --- | --- | --- | --- |
| Usuario autenticado | Descargar su alcance personal | Acceder sin token | `SgdApiClient.login` y token Bearer |
| Usuario con permiso de oficina | Elegir alcance oficina | Acceder a oficina no autorizada | `can_download_office` recibido del SGD |
| Aplicacion local | Leer y copiar datos autorizados | Alterar documentos remotos | Solo usa consultas y descargas del contrato externo |

## Reglas Funcionales

1. La base activa pertenece a un usuario, periodo, alcance y oficina. No se
   deben mostrar ni exportar registros de otro contexto.
2. La vista previa y el Excel muestran principales; los relacionados se abren
   bajo demanda y se cuentan en la columna correspondiente.
3. Los relacionados se resuelven por lotes, no con una solicitud por documento.
4. La descarga de archivos parte del inventario local `files`; no vuelve a listar
   documentos. Debe registrar su resultado por destino fisico.
5. Los adjuntos relacionados se guardan dentro de la carpeta de su principal y
   se prefijan con el nombre del relacionado para evitar colisiones.
6. Cambiar la URL del servicio cierra la sesion. La clave nunca se guarda.

## Estados Operativos

| Estado | Evento | Resultado |
| --- | --- | --- |
| Sin sesion | Login valido | Sesion activa y oficinas disponibles |
| Sesion activa | Descargar registros | Worker sincroniza SQLite y actualiza progreso |
| Sesion activa con base | Descargar archivos | Worker revisa y descarga tareas del catalogo |
| Worker activo | Cancelar | Finaliza la solicitud o archivo actual y se detiene |
| Sesion activa | Logout o cambio de URL | Token local descartado y controles deshabilitados |

## Errores Y Recuperacion

| Situacion | Comportamiento | Recuperacion |
| --- | --- | --- |
| `429` del SGD | Reintento con espera limitada | Esperar y dejar que el cliente agote reintentos |
| Archivo `404` | Registrar error de tarea | Corregir storage del SGD o reintentar despues |
| Archivo parcial | Queda con sufijo `.part` | La proxima descarga sobrescribe el destino final |
| Cambio de contexto | Base documental distinta o limpia | Volver a sincronizar el contexto seleccionado |

## Pruebas Minimas

1. Un login valida oficinas y alcances habilitados por el SGD.
2. Una sincronizacion con relacionados conserva `master_id` y no bloquea la UI.
3. Una descarga cancelada puede reanudarse sin repetir archivos validos.

## Decisiones Vigentes

| Fecha | Decision | Motivo | Consecuencia |
| --- | --- | --- | --- |
| 2026-09-01 | Separar registros de archivos | Evitar relistar documentos al bajar adjuntos | Dos SQLite por contexto |
| 2026-09-01 | Agrupar adjuntos por tipo y rango de 1000 | Evitar directorios planos grandes | El numero documental define el rango |
