# Pendientes Y Riesgos

## Pendientes

- Ejecutar pruebas manuales contra un SGD con storage real de adjuntos.
- Confirmar con el backend que `meta.related_total` es estable entre paginas de
  un mismo lote de relacionados.
- Incorporar pruebas automatizadas de almacenamiento, exportacion y tareas de
  descarga reanudable.
- Probar el ejecutable en una maquina Windows limpia con `sgd_service.json`
  ausente y presente.

## Riesgos Vigentes

- El permiso de oficina y el acceso a archivos son decisiones del backend SGD;
  la aplicacion solo transmite contexto y `master_id` cuando corresponde.
- Un `404` de descarga puede significar que el archivo no esta montado en el
  backend. El catalogo local conserva el error para reintento.
- Los nombres sanitizados pueden colisionar en casos excepcionales; el catalogo
  usa la ruta relativa como identidad de descarga.
- No hay suite automatizada del proyecto; cada entrega requiere compilacion y
  pruebas manuales documentadas.
