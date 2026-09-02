# Contexto Del Proyecto

## Objetivo

Construir una aplicacion de escritorio para descargar documentos emitidos desde el sistema SGD del GORE. La aplicacion debe permitir que cada usuario descargue sus documentos personales y, si tiene permisos de jefe, tambien los documentos emitidos a nombre de su oficina.

El objetivo final es que pueda empaquetarse como `.exe` para Windows, pero durante el desarrollo se puede ejecutar con Python.

## Repositorios Involucrados

- Backend SGD: `/home/administrador/sgd-gore`
- Aplicacion de escritorio: `/home/administrador/cargos_downloader`
- Notebook historico usado como referencia: `/home/administrador/pry-web-desk/cargos.ipynb`

## Problema Original

El notebook `cargos.ipynb` leia directamente la base de datos, obtenia documentos principales, buscaba documentos relacionados mediante `tram_operacion.oper_iddocumento_adj`, obtenia archivos desde `tram_file` y descargaba usando rutas web publicas como:

```text
/tramite/documento/printR/{file_id}/{documento_id}.pdf
```

Ese enfoque funcionaba para descargar masivamente, pero tenia problemas:

- No identificaba de forma segura quien descargaba.
- No aplicaba autorizacion por usuario, jefe u oficina.
- Dependia de consultas directas a base de datos desde fuera del SGD.
- Usaba endpoints web no pensados como API de descarga masiva.
- Generaba muchas carpetas planas por tipo de documento, afectando el rendimiento del sistema de archivos.

## Solucion Adoptada

La solucion se dividio en dos etapas:

1. Adecuar el backend SGD con una API especifica para cargos.
2. Construir una aplicacion de escritorio en Python que consuma esa API.

La etapa 1 ya fue implementada en `sgd-gore` con rutas bajo:

```text
/api/cargos
```

La etapa 2 esta en desarrollo en este proyecto.

## Decisiones Importantes

- La aplicacion de escritorio usa Python.
- La GUI usa PySide6, no tkinter, porque tkinter no estaba instalado en el entorno WSL usado inicialmente.
- El `.exe` debe generarse en Windows, no desde WSL.
- El venv no debe copiarse entre WSL y Windows; debe recrearse en cada sistema operativo.
- La URL del servicio SGD es configurable desde la interfaz.
- Por defecto, la URL es:

```text
http://localhost:8079
```

## Estado Actual

El backend SGD tiene rutas operativas y probadas en Docker con el usuario de desarrollo autorizado.

La aplicacion Python ya tiene:

- Cliente HTTP para la API SGD.
- Ventana de escritorio.
- Login.
- Seleccion de oficina.
- Alcance personal/oficina.
- Rango de fechas.
- Carpeta destino.
- Agrupacion por rangos.
- Descarga de documentos principales y relacionados.
- Scripts de desarrollo y empaquetado.

Pendiente principal:

- Probar la app completa desde Windows con GUI real.
- Montar o apuntar el backend SGD a los archivos reales para validar descarga fisica.
- Ajustar UX si aparecen casos reales no contemplados.
