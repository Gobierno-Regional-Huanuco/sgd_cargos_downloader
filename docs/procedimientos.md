# Procedimientos

## Mantenimiento de memoria

Antes de modificar un flujo funcional, revisar [guia_IA.md](guia_IA.md) y el
`context.md` del módulo afectado. Actualizar arquitectura, contrato externo,
modelo de datos y contexto cuando cambie su comportamiento real. Ejecutar el
validador y la compilación antes de cerrar el trabajo.

## Ejecutar En Desarrollo

En PowerShell:

```powershell
cd D:\cargos_downloader
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
