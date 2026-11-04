# Historial de cambios

Este proyecto sigue [Versionado Semantico](https://semver.org/lang/es/).

## 0.2.0-rc.1 - 2026-11-03

Segunda version candidata: reporte unico filtrable por origen y usuario, y
adjuntos organizados por usuario.

### Cambiado

- La exportacion genera un unico libro por contexto, con hoja `EXTERNOS` y
  columnas `Origen` y `Registrado por` filtrables en todas las hojas. Se
  retiran los libros separados de manuales/externos y personales por usuario.
- Los documentos con clasificacion invalida se exportan como `Sin clasificar`
  con aviso, en lugar de bloquear la exportacion.
- Los adjuntos personales y externos se guardan en `_PERSONALES` y
  `_EXTERNOS` por usuario; los ya descargados se reubican sin volver a bajarse.
- Esquema SQLite 7: columnas de clasificacion completadas desde el JSON local.
- `Registrado por` muestra el nombre solo cuando se deduce sin duda de los
  documentos personales; en otro caso muestra solo el ID.

### Corregido

- El titulo del Excel se combina en todo el ancho de la tabla.
- Los numeros no numericos ya no se rellenan con ceros en carpetas y usan el
  rango `SIN NUMERO`; los externos sin siglas agregan su Reg. SGD.

### Compatibilidad

- Al abrir una base local con esta version se migra al esquema 7. Para volver
  a `0.1.0-rc.1` basta restaurar el ejecutable anterior; si despues se regresa
  a esta version, usar `Limpiar base` y volver a descargar los registros para
  reclasificar lo sincronizado con la version anterior.

## 0.1.0-rc.1 - 2026-10-22

Primera version candidata para validacion interna y exposicion controlada.

### Agregado

- Descarga local de documentos principales, relacionados y archivos del SGD.
- Exportacion Excel separada para oficina, manuales/externos y documentos
  personales por usuario.
- Oficinas destinatarias, CUI, tipo de tramite, numeracion documental completa,
  correlativo y registro SGD en los reportes.
- Diagnosticos detallados para documentos con datos de clasificacion invalidos.
- Version visible en la aplicacion y metadatos del ejecutable Windows.
- Paquete ZIP versionado y checksum SHA-256 para cada release Windows.
