# SGD Cargos Downloader

Aplicacion de escritorio en Python para registrar documentos emitidos desde la
API `/api/cargos` del SGD, generar un Excel de registro y descargar sus
archivos adjuntos.

## Requisitos e instalacion inicial

- Python 3.10 o superior, disponible en el `PATH`.
- Git Bash o WSL si se va a ejecutar el validador de memoria
  (`scripts/validate-project-memory`).

En los comandos, `<ruta-del-proyecto>` es la carpeta donde clonaste este
repositorio (puede ser cualquiera, no depende de una unidad o ruta fija).

Crear el entorno virtual la primera vez (Windows):

```powershell
cd <ruta-del-proyecto>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En Bash/Linux:

```bash
cd <ruta-del-proyecto>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Detalle completo, verificacion y pasos siguientes en
[docs/procedimientos.md](docs/procedimientos.md#instalar-entorno-primera-vez).

## Desarrollo

En Windows PowerShell:

```powershell
cd <ruta-del-proyecto>
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python -m cargos_downloader.main
```

Tambien puedes usar el script:

```powershell
cd <ruta-del-proyecto>
.\scripts\run_dev.ps1
```

En Bash/Linux:

```bash
cd <ruta-del-proyecto>
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m cargos_downloader.main
```

La URL del servicio SGD se guarda junto al ejecutable en `sgd_service.json`:

```json
{
  "service_url": "http://localhost:8079"
}
```

Al ejecutar el `.exe` sin ese archivo, o con una URL vacia, la aplicacion la
solicita antes de iniciar sesion. Tambien puede cambiarse desde
`Configuracion`; el cambio actualiza ese JSON y cierra la sesion activa.

## Empaquetar en Windows

Ejecutar en Windows, dentro de esta carpeta:

```powershell
.\scripts\build_windows.ps1
```

El ejecutable queda en:

```text
dist\SGD-Cargos-Downloader.exe
```

El empaquetado deja tambien `dist\sgd_service.json`. Distribuir ambos archivos en la misma carpeta.

## Salidas

El `Destino raiz` se organiza por usuario, periodo y alcance:

```text
{Destino raiz}\{usuario}\{periodo}\{personal|oficina}
```

Por ejemplo:

```text
C:\Users\usuario\Downloads\cargos_sgd\waguirre\2023\personal
```

En esa carpeta activa se generan:

- `cargos_sgd.sqlite`: base de datos local portable con los registros sincronizados.
- `descargas_archivos.sqlite`: catalogo persistente del estado de cada archivo descargado.
- `registro_documentos_{periodo}_{alcance}_{oficina}.xlsx`: reporte Excel con
  una hoja por tipo de documento del periodo.
- Archivos adjuntos en la estructura por tipo/rango/documento.

La interfaz separa tres acciones:

- `Descargar registros`: consulta el SGD y actualiza solo `cargos_sgd.sqlite`.
- `Descargar archivos`: usa los arreglos `files` ya guardados localmente; no
  vuelve a consultar los listados de documentos.
- `Exportar Excel`: se habilita solo con sesion iniciada y registros descargados
  para el contexto seleccionado.
- `Limpiar base`: elimina solo el registro documental; conserva archivos, catalogo y Excel.
- `Configuracion`: abre los parametros tecnicos de descarga: URL SGD, carpeta
  destino, tamanio de pagina, tamanio de lotes y relacionados.

La pantalla principal muestra el contexto de trabajo, el avance real de registros
procesados y una vista previa de las hojas que se exportaran al Excel. El detalle
de acciones queda plegado debajo de la barra de progreso.

La vista previa muestra solo documentos principales. Los relacionados se revisan
desde `Ver relacionados` o con doble clic sobre un principal. Para evitar
bloqueos, la tabla en pantalla se carga en segundo plano y muestra hasta 300
filas por hoja; el Excel exporta todos los registros principales.

## Notas

- El token se obtiene mediante `POST /api/cargos/login` y se revoca con `POST /api/cargos/logout`.
- La aplicacion no guarda la clave del usuario.
- La URL SGD vive en `sgd_service.json` junto al ejecutable; cambiarla cierra la
  sesion activa y obliga a iniciar sesion nuevamente.
- La aplicacion recuerda el ultimo usuario. Si encuentra bases locales con datos
  para ese usuario, bloquea el campo `Usuario` y solo pide la clave.
- `Cambiar usuario` elimina las bases locales del usuario activo antes de
  permitir ingresar otro usuario.
- El log persistente queda en `%USERPROFILE%\.sgd_cargos_downloader\app.log`.
- El periodo disponible empieza en 2023 y se consulta como rango anual completo.
- El reporte clasifica como `Digital` los documentos con archivos y como
  `Fisico` los documentos sin archivos.
- La columna `Expediente y Documento` usa `docu_idexma / iddocumento`.
- La columna `Firmante` se muestra junto al numero de documento y usa `docu_firma`.
- El Excel exporta solo documentos principales y agrega una columna
  `Relacionados` con la cantidad de documentos vinculados.
- La base SQLite se limpia automaticamente cuando cambia el contexto de
  descarga: periodo, alcance u oficina.
- Los documentos relacionados se consultan por lotes con
  `POST /api/cargos/documentos/relacionados/batch`; no se consulta uno por uno.
- Las descargas se agrupan por tipo de documento y rangos de correlativo; por
  ejemplo, `INFORME\000001-001000\INFORME 000001 GRH_GRI`.
- Si el storage de archivos no esta montado en el contenedor SGD, las descargas
  pueden devolver `404`, aunque la consulta de documentos funcione.
