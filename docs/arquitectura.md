# Arquitectura

## Proposito

SGD Cargos Downloader es una aplicacion de escritorio Windows que consume la
API existente del SGD. Registra documentos emitidos, conserva una copia local
por usuario y contexto, exporta un libro Excel y descarga los adjuntos que ya
fueron inventariados.

La aplicacion no publica una API ni accede directamente a la base de datos del
SGD. El SGD conserva la autoridad sobre autenticacion, permisos, documentos y
archivos remotos.

## Stack

- Python y PySide6 para la aplicación de escritorio.
- `requests` para el consumo HTTP autenticado del SGD.
- SQLite para el registro local y el catálogo de archivos descargados.
- `openpyxl` para la exportación del formato de cargos.

## Componentes

```text
Usuario
  -> PySide6 MainWindow
     -> SgdApiClient -> API /api/cargos del SGD
     -> downloader -> SQLite local y archivos locales
     -> excel_exporter -> libro XLSX
```

| Componente | Responsabilidad | Limite |
| --- | --- | --- |
| `ui.py` | Interaccion, sesion, hilos, progreso y vistas previas | No implementa consultas HTTP ni SQL de dominio |
| `api.py` | Autenticacion y transporte HTTP con reintentos de 429 | No interpreta exportacion ni guarda datos locales |
| `downloader.py` | Sincronizacion paginada, relaciones por lote y descarga reanudable | No dibuja UI |
| `storage.py` | Esquema SQLite, migracion, contexto y catalogo de archivos | No conoce widgets ni credenciales |
| `excel_exporter.py` | Vista previa y XLSX de documentos principales | No consulta al SGD |
| `config.py` | Preferencias locales y URL portable del servicio | No guarda claves ni tokens |

## Flujo global

1. La aplicacion carga `sgd_service.json` junto al ejecutable. Si falta una URL,
   la solicita antes de iniciar sesion.
2. El usuario inicia sesion ante el SGD y selecciona oficina, alcance y periodo.
3. `Descargar registros` consulta principales por paginas y relacionados por
   lotes, guardandolos en `cargos_sgd.sqlite`.
4. `Descargar archivos` usa los arreglos `files` guardados y actualiza
   `descargas_archivos.sqlite` mientras descarga los pendientes.
5. `Exportar Excel` genera un reporte de principales por tipo documental.

## Limites De Contexto

La salida activa siempre se delimita por usuario, periodo y alcance:

```text
{destino_raiz}\{usuario}\{periodo}\{personal|oficina}
```

La oficina completa el contexto de cada consulta y se guarda en SQLite. Cambiar
periodo, alcance u oficina no debe mezclar registros de otra consulta.

## Concurrencia Y Recuperacion

Las operaciones largas se ejecutan en `QThread`; la UI recibe senales de
progreso y log. La cancelacion se observa entre solicitudes o archivos. Cada
archivo se escribe primero como `.part` y el catalogo permite reanudar despues.

Las decisiones funcionales estan en
[context.md](../src/cargos_downloader/context.md). El detalle de tablas esta en
[modelo-datos.md](modelo-datos.md).
