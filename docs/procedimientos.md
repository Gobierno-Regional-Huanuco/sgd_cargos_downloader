# Procedimientos

## Mantenimiento de memoria

Antes de modificar un flujo funcional, revisar [guia_IA.md](guia_IA.md) y el
`context.md` del módulo afectado. Actualizar arquitectura, contrato externo,
modelo de datos y contexto cuando cambie su comportamiento real. Ejecutar el
validador y la compilación antes de cerrar el trabajo.

## Instalar Entorno (Primera Vez)

Requiere Python 3.10 o superior instalado y disponible en el `PATH` (ver
[entorno.md](entorno.md)). En los comandos, `<ruta-del-proyecto>` es la
carpeta donde se clono este repositorio; no depende de una unidad ni ruta
fija.

En PowerShell (Windows):

```powershell
cd <ruta-del-proyecto>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En Bash/Linux o WSL:

```bash
cd <ruta-del-proyecto>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

El `.venv` es local a cada sistema operativo; no se comparte entre Windows y
WSL. Verificar la instalacion:

```powershell
.\.venv\Scripts\python.exe -c "import PySide6, requests; print('OK')"
```

Con el entorno creado, la app necesita ademas `sgd_service.json` con la URL del
SGD (ver [entorno.md](entorno.md)); si falta, la aplicacion la pide al iniciar.
Para verificar que el SGD configurado responde antes de abrir la interfaz, ver
[pruebas-conexion-sgd.md](pruebas-conexion-sgd.md).

## Ejecutar En Desarrollo

En PowerShell:

```powershell
cd <ruta-del-proyecto>
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python -m cargos_downloader.main
```

El script equivalente es `./scripts/run_dev.ps1`. En Linux o WSL se usa
`scripts/run_dev.sh` con un entorno virtual creado para ese sistema.

## Empaquetar Y Distribuir

```powershell
.\scripts\build_windows.ps1
```

La distribucion requiere ambos archivos de `dist`:

```text
SGD-Cargos-Downloader.exe
sgd_service.json
```

Antes de entregar, abrir el ejecutable en una carpeta limpia, verificar que
solicita una URL si falta el JSON y comprobar que puede guardar una URL valida.

## Validacion Tecnica

Compilar los modulos Python:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m compileall -q src
```

El validador de memoria es de solo lectura y requiere Git Bash o WSL:

```bash
scripts/validate-project-memory
```

La copia local del validador ignora `gestionar-memoria-viva-proyecto` porque es
la herramienta de instalación con plantillas intencionales, no código ni
documentación del producto. La excepción se limita a esa carpeta.

Ejecutar Markdownlint desde una herramienta disponible en el entorno. Si no se
instala Node o Markdownlint, declararlo como validacion omitida; no presentar
esa ausencia como conformidad.

## Prueba Manual Minima

1. Iniciar sin `sgd_service.json` y registrar una URL valida.
2. Iniciar sesion y comprobar oficinas y alcances permitidos.
3. Descargar registros de un periodo y verificar el progreso.
4. Abrir relacionados, exportar Excel y comprobar que solo hay principales.
5. Descargar archivos, cancelar una ejecucion y reanudarla.
6. Limpiar la base y confirmar que se conservan adjuntos y catalogo.
7. Cerrar sesion y confirmar que no se conserva la clave.
