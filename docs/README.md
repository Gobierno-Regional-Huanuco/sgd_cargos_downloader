# Documentacion

Esta carpeta resume el contexto necesario para continuar el desarrollo del descargador de cargos SGD.

## Orden Sugerido De Lectura

1. [Contexto del proyecto](01-contexto.md)
2. [API requerida en SGD](02-backend-sgd-api.md)
3. [Flujo de la aplicacion](03-flujo-aplicacion.md)
4. [Estructura del proyecto Python](04-estructura-proyecto.md)
5. [Desarrollo y empaquetado en Windows](05-desarrollo-windows.md)
6. [Pendientes y riesgos](06-pendientes-y-riesgos.md)

## Resumen Corto

El backend SGD expone `/api/cargos`. La app Python consume esa API para autenticar usuarios, listar oficinas, consultar documentos emitidos y descargar archivos autorizados.

Para Windows:

```powershell
cd C:\dev\cargos_downloader
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m cargos_downloader.main
```

Para generar `.exe`:

```powershell
.\scripts\build_windows.ps1
```
