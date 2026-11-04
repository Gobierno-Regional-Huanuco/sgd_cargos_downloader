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
   se prefijan con el nombre del relacionado para evitar colisiones. La
   carpeta base depende del origen del principal: oficina y sin clasificar en
   la raiz del contexto, personales en `_PERSONALES\{usuario}` y
   manuales/externos o PIDE en `_EXTERNOS\{usuario}`, donde `{usuario}` es la
   etiqueta de la regla 12 o `SIN USUARIO`. Un externo sin siglas agrega
   `[Reg {iddocumento}]` a su carpeta y un numero no numerico usa el rango
   `SIN NUMERO`. Si un adjunto ya descargado cambia de ruta, se mueve
   localmente y conserva su estado sin volver a descargarse.
6. Cambiar la URL del servicio cierra la sesion. La clave nunca se guarda.
7. El reporte muestra `oficinas_destinatarias` tal como lo entrega el SGD en
   una sola celda por documento. Un valor nulo, vacio o ausente deja la celda
   vacia y nunca oculta el documento ni se reemplaza con otra oficina.
8. El reporte agrega CUI y Tipo de trámite, en ese orden, despues de las
   columnas documentales existentes. Usa `cui_proyecto` y
   `tipo_tramite_descripcion`; `tipo_tramite` se conserva como identificador
   interno y no se presenta al usuario. Los valores nulos, vacios o ausentes
   dejan celdas vacias sin retirar la fila.
9. `N. Documento` muestra tipo, correlativo, anio y siglas con el formato
   `TIPO 000000-AAAA-SIGLAS`. El correlativo anterior se conserva en la columna
   `Numero correlativo`; si falta fecha o siglas, la numeracion visible conserva
   solo el correlativo y no inventa componentes.
10. `Reg. SGD` es la ultima columna del reporte y conserva directamente
    `iddocumento` para facilitar cruces y calculos, sin modificar la cantidad ni
    el orden de las filas.
11. La exportacion genera siempre un unico libro por contexto. Oficina,
    personales y documentos sin clasificar comparten las hojas por tipo
    documental; los manuales/externos y los de interoperabilidad/PIDE van a la
    hoja `{periodo} EXTERNOS`, que agrega la columna Tipo y solo existe cuando
    hay externos. La clasificacion vive en `classification.py` y usa
    `docu_origen` (`1` interno, `2` manual/externo, `3` PIDE) y `docu_tipo`
    (`0` oficina, `1` personal; nulo equivale a `0`). Un personal exige un
    usuario valido. Un documento con clasificacion invalida no bloquea la
    exportacion: se exporta con Origen `Sin clasificar` y se informan
    cantidades y una muestra de IDs por causa en un aviso y en el log.
12. Todas las hojas agregan Origen y Registrado por antes de `Reg. SGD`, con
    filtro automatico y encabezado fijo para filtrar por ambos. Quien registra
    es `docu_idusuario`, con respaldo temporal en `oper_idusuario` solo cuando el
    primero esta ausente o es nulo. El SGD no envia su nombre: se deduce solo
    de los documentos personales del contexto, nunca de firmantes de oficina o
    externos, y solo cuando no hay duda: todos los personales del usuario
    tienen el mismo firmante y ese firmante no aparece en los personales de
    otro usuario. Entonces se muestra `{id} - {nombre}`; en cualquier otro caso
    se muestra solo el `{id}`. El ID es la referencia que separa filtros y
    carpetas. Esta deduccion es provisional hasta contar con el listado oficial
    de usuarios.

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
4. Una exportacion de oficina con personales y externos genera un solo libro
   con la hoja de externos y las columnas Origen y Registrado por.

## Decisiones Vigentes

| Fecha | Decision | Motivo | Consecuencia |
| --- | --- | --- | --- |
| 2026-09-01 | Separar registros de archivos | Evitar relistar documentos al bajar adjuntos | Dos SQLite por contexto |
| 2026-09-01 | Agrupar adjuntos por tipo y rango de 1000 | Evitar directorios planos grandes | El numero documental define el rango |
| 2026-11-03 | Un unico libro con Origen y Registrado por | Filtrar por usuario sin multiplicar archivos | Se retiran los libros de externos y personales por usuario |
| 2026-11-03 | Adjuntos externos y personales en carpetas por usuario | Separar lo que cada usuario registra | Los adjuntos ya descargados se reubican localmente |
