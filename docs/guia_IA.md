# Guia Para Agentes

## Adopción del estándar

- Skill: `gestionar-memoria-viva-proyecto`.
- Versión adoptada: `1.6.0`.
- Fecha de revisión: `2026-09-02`.
- Version anterior: no aplica.

Leer [AGENTS.md](../AGENTS.md) antes de cambiar el repositorio. Esa es la
fuente del protocolo; esta guia solo permite encontrar la memoria aplicable.

## Fuentes Normativas

| Pregunta | Fuente |
| --- | --- |
| Arquitectura y flujo entre componentes | [arquitectura.md](arquitectura.md) |
| Reglas de desarrollo Python de escritorio | [.github/instructions/python-desktop.instructions.md](../.github/instructions/python-desktop.instructions.md) |
| Convenciones compartidas | [convenciones.md](convenciones.md) |
| Entorno, configuracion y distribucion | [entorno.md](entorno.md) |
| Comandos y validaciones | [procedimientos.md](procedimientos.md) |
| Persistencia local | [modelo-datos.md](modelo-datos.md) |
| Contrato HTTP externo consumido | [api.md](api.md) |
| Reglas funcionales del descargador | [context.md](../src/cargos_downloader/context.md) |
| Protocolo y referencias de memoria viva | [memoria-viva/README.md](memoria-viva/README.md) |

## Flujos Criticos

| Flujo | Riesgo | Fuente | Verificacion |
| --- | --- | --- | --- |
| Sincronizar registros | No mezclar periodo, alcance, oficina o usuario | [context.md](../src/cargos_downloader/context.md) | Compilacion y prueba manual con un contexto real |
| Descargar adjuntos | No repetir listados ni perder el avance local | [context.md](../src/cargos_downloader/context.md) | Reintento de una descarga interrumpida |
| Exportar Excel | Solo exportar principales del contexto activo | [modelo-datos.md](modelo-datos.md) | Exportacion y revision del libro generado |

## Contextos de módulos

- `cargos_downloader`: [src/cargos_downloader/context.md](../src/cargos_downloader/context.md)
  - aplicacion de escritorio para registrar y descargar cargos autorizados del SGD.

## Capas

- `python-desktop`:
  [reglas de escritorio](../.github/instructions/python-desktop.instructions.md)
  - GUI PySide6, integracion HTTP, persistencia SQLite y empaquetado Windows.

## Capacidades No Aplicables

- `docs/cli.md` no aplica: el proyecto no publica una interfaz CLI con
  argumentos, salida y codigos propios; `python -m cargos_downloader.main` solo
  arranca la GUI.
- `docs/frontend.md` no aplica: no hay una raiz frontend web convencional. La
  UI PySide6 pertenece a la capa Python de escritorio.
