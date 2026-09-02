# Entorno

## Requisitos

| Elemento | Uso |
| --- | --- |
| Python 3.10 o superior | Ejecutar la aplicacion y el validador |
| PySide6 | Interfaz de escritorio |
| requests | Cliente HTTP del SGD |
| PyInstaller | Empaquetado Windows |
| Git Bash o WSL | Ejecutar el validador POSIX |

Las dependencias Python estan declaradas en `requirements.txt`. El entorno
virtual `.venv` es local y no debe compartirse entre Windows y WSL.

## Servicios

`sgd_service.json`, ubicado junto al ejecutable distribuido, contiene la URL
raiz del SGD:

```json
{
  "service_url": "http://localhost:8079"
}
```

El archivo no contiene claves ni tokens. Si no existe, la aplicacion solicita
una URL HTTP o HTTPS y la crea cuando el directorio permite escritura. Cambiar
la URL desde la configuracion cierra la sesion actual.

## Variables

| Variable o archivo | Uso | Valor o comportamiento |
| --- | --- | --- |
| `PYTHONPATH` | Resolver el paquete fuente al ejecutar en desarrollo | `src` |
| `sgd_service.json` | URL base editable del servicio SGD | Se busca junto al ejecutable o al directorio de trabajo |
| `CARGOS_SGD_URL` | No se usa | La configuración se resuelve exclusivamente desde el archivo JSON |

## Datos Locales

El destino por defecto es `Downloads\cargos_sgd`. Cada contexto contiene las
bases SQLite, el Excel y los adjuntos. Las claves y tokens viven solo en memoria;
el log local no debe imprimirlos.

## Integracion Externa

El SGD debe estar disponible en la URL configurada y exponer `/api/cargos`.
Para descargar adjuntos, el storage que usa el backend SGD debe estar montado y
ser legible por ese backend. Un `404` de archivo puede indicar ausencia fisica,
no necesariamente falta de permiso.

Los detalles del contrato consumido viven en [api.md](api.md); los comandos de
instalacion y empaquetado viven en [procedimientos.md](procedimientos.md).
