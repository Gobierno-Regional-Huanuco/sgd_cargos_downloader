# Estructura Del Proyecto Python

Raiz:

```text
/home/administrador/cargos_downloader
```

## Archivos

```text
requirements.txt
README.md
scripts/run_dev.sh
scripts/build_linux.sh
scripts/build_windows.ps1
src/cargos_downloader/main.py
src/cargos_downloader/ui.py
src/cargos_downloader/api.py
src/cargos_downloader/downloader.py
src/cargos_downloader/config.py
```

## Modulos

### `main.py`

Punto de entrada.

Ejecuta:

```python
run_app()
```

### `ui.py`

Interfaz grafica con PySide6.

Responsabilidades:

- Mostrar formulario de URL SGD.
- Login/logout.
- Mostrar usuario autenticado.
- Listar oficinas.
- Elegir alcance.
- Elegir fechas.
- Elegir carpeta destino.
- Iniciar/cancelar descarga.
- Mostrar bitacora de progreso.

Usa `DownloadThread` para que la descarga no congele la UI.

### `api.py`

Cliente HTTP con `requests`.

Responsabilidades:

- Login.
- Logout.
- Consultar usuario actual.
- Consultar oficinas.
- Consultar documentos.
- Consultar relacionados.
- Descargar archivos por streaming.
- Normalizar errores HTTP en `SgdApiError`.

### `downloader.py`

Motor de descarga.

Responsabilidades:

- Recorrer paginas de documentos.
- Descargar archivos principales.
- Consultar y descargar relacionados.
- Crear estructura de carpetas.
- Sanitizar nombres de archivos.
- Calcular rangos `000001-001000`, etc.
- Omitir archivos ya existentes.

### `config.py`

Lectura y escritura de configuracion local en JSON.

Archivo usado:

```text
~/.sgd_cargos_downloader/config.json
```

## Dependencias

```text
PySide6
requests
pyinstaller
```

## Estado Del Venv

El venv es local y no debe versionarse:

```text
.venv/
```

Si se mueve la carpeta del proyecto, conviene eliminar y recrear el venv. Los venv guardan rutas absolutas internas.

## Notas Para Agentes

- No guardar credenciales en archivos.
- No imprimir tokens en logs de usuario.
- Si se prueba login real, llamar logout al terminar.
- En WSL puede fallar la GUI por falta de Wayland/XCB; eso no implica error de codigo.
- El `.exe` debe construirse desde Windows.
- No depender de `cargos.ipynb` para ejecucion final; solo es referencia historica.
- La app debe consumir solamente la API `/api/cargos`.
