---
applyTo: "src/cargos_downloader/**/*.py"
---

# Capa Python De Escritorio

Aplicar primero `AGENTS.md`, [convenciones.md](../../docs/convenciones.md) y el
[contexto del modulo](../../src/cargos_downloader/context.md).

## Alcance

- Ruta principal: `src/cargos_downloader`.
- Responsabilidad: GUI PySide6, cliente HTTP del SGD, SQLite local, exportacion
  XLSX y empaquetado Windows.
- Limites: no introducir acceso directo a la base de datos del SGD, no persistir
  claves o tokens y no actualizar widgets desde workers.

## Reglas Especificas

- Toda operacion que pueda bloquear la UI usa `QThread` y senales.
- Mantener las consultas HTTP en `api.py`, la persistencia en `storage.py` y la
  coordinacion de descargas en `downloader.py`.
- Usar `Path` para rutas y sanitizar nombres de archivos antes de escribirlos.
- Mantener `sgd_service.json` junto al ejecutable como fuente de URL portable.

## Validaciones

Ejecutar la compilacion Python de [procedimientos.md](../../docs/procedimientos.md)
y las pruebas manuales del flujo afectado. Ejecutar tambien
`scripts/validate-project-memory` desde Git Bash o WSL antes de cerrar cambios
estructurales o documentales.
