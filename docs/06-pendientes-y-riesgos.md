# Pendientes Y Riesgos

## Pendientes Funcionales

- Probar la aplicacion en Windows con GUI real.
- Probar descarga fisica cuando el backend tenga montado el storage de PDFs.
- Confirmar con usuarios reales la definicion exacta de "documentos emitidos a nombre de la oficina".
- Decidir si el alcance oficina debe incluir documentos personales de la oficina por defecto o solo con opcion marcada.
- Agregar barra de progreso por cantidad de archivos si el backend expone conteos o si la app hace preconsulta.
- Agregar reintentos automaticos para errores transitorios de red.
- Agregar manifest local de descarga para trazabilidad y reanudacion mas robusta.

## Riesgos Backend

### Endpoints Publicos Antiguos

El SGD todavia tiene rutas historicas de documentos que no necesariamente pasan por la nueva autorizacion. La app nueva no debe usarlas.

Rutas historicas como estas fueron usadas por el notebook:

```text
/tramite/documento/printR/{file_id}/{documento_id}.pdf
```

La solucion nueva debe consumir:

```text
/api/cargos/archivos/{archivo}/download
```

### Permisos De Jefe

La API considera jefe si:

- `adm_esjefe` es verdadero.
- Tiene permiso `tramite.reporte.jefe`.
- Tiene permiso `tramite.reporte.global`.
- Tiene rol `JEFE`.

Esto fue elegido para ser compatible con el estado actual del sistema. Si produccion define otra regla, actualizar `canDownloadOfficeDocuments()`.

### Consulta De Oficina Muy Grande

La oficina puede devolver muchos documentos. Por eso la API usa `simplePaginate()` por defecto. Evitar `with_total=1` salvo que sea realmente necesario.

## Riesgos App

### WSL Y GUI

PySide6 necesita entorno grafico. En WSL puede fallar con errores de Wayland/XCB:

```text
Could not load the Qt platform plugin "xcb"
Failed to create wl_display
```

Eso no implica error de la app. Para uso normal y empaquetado, ejecutar en Windows.

### Nombres De Archivo

La app limpia caracteres invalidos para Windows:

```text
< > : " / \ | ? *
```

Tambien limita nombres largos. Si aparecen colisiones de nombres, mejorar `file_name()` para agregar `file_id`.

### Archivos Grandes

La descarga usa streaming y escribe primero `.part`. Si se interrumpe, puede quedar un archivo parcial. En una mejora posterior se puede limpiar o reanudar.

## Recomendaciones Para La Siguiente Iteracion

1. Copiar proyecto a Windows.
2. Recrear venv.
3. Ejecutar GUI.
4. Login contra `http://localhost:8079`.
5. Probar rango pequeno de fechas.
6. Montar storage de PDFs o probar contra un SGD que tenga archivos.
7. Ajustar comportamiento real de carpetas y nombres segun expectativa del usuario final.
