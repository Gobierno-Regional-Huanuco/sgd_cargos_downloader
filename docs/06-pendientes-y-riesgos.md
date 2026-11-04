# Pendientes Y Riesgos

## Pendientes

- Ejecutar pruebas manuales contra un SGD con storage real de adjuntos.
- Confirmar con el backend que `meta.related_total` es estable entre paginas de
  un mismo lote de relacionados.
- Ampliar las pruebas automatizadas a la sincronizacion paginada de
  principales y relacionados (`run_download`), hoy cubierta solo manualmente.
- Validar la hoja de externos y las carpetas `_EXTERNOS` con una oficina que
  registre documentos manuales/externos o PIDE.
- Incorporar el listado oficial de usuarios que exportara Modernizacion para
  mostrar con confianza el nombre de quien registra.
- Probar el ejecutable en una maquina Windows limpia con `sgd_service.json`
  ausente y presente.

## Riesgos Vigentes

- El permiso de oficina y el acceso a archivos son decisiones del backend SGD;
  la aplicacion solo transmite contexto y `master_id` cuando corresponde.
- Un `404` de descarga puede significar que el archivo no esta montado en el
  backend. El catalogo local conserva el error para reintento.
- Los nombres sanitizados pueden colisionar en casos excepcionales; el catalogo
  usa la ruta relativa como identidad de descarga.
- El SGD no entrega el nombre de quien registra. `Registrado por` solo deduce
  el nombre de los personales cuando el firmante es unico para ese usuario y no
  se repite en otro; en datos reales de 2024 dos pares de IDs compartian
  firmante y quedan solo con su ID. Persiste un caso no detectable: un usuario
  cuyos personales firma siempre otra persona que no aparece con otro ID.
- La suite automatizada (`unittest`) cubre exportacion, migracion de esquema,
  clasificacion y organizacion de adjuntos, pero no la interfaz ni el consumo
  real del SGD; cada entrega sigue requiriendo la prueba manual documentada.
