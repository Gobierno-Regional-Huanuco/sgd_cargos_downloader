# Flujo De La Aplicacion De Escritorio

## Flujo General

1. El usuario abre la aplicacion.
2. Configura la URL del servicio SGD.
3. Ingresa usuario y clave.
4. La app llama a `POST /api/cargos/login`.
5. El backend devuelve token, datos del usuario, permisos y oficinas.
6. La app muestra oficinas disponibles.
7. El usuario elige:
   - Oficina.
   - Alcance: personal u oficina.
   - Rango de fechas.
   - Carpeta destino.
   - Tamano de grupo.
   - Si incluye documentos relacionados.
8. La app consulta documentos por paginas.
9. Por cada documento principal descarga sus archivos.
10. Si esta habilitado, consulta documentos relacionados y descarga sus archivos.
11. Al terminar o cerrar la app, llama a logout para revocar el token.

## Alcances

### Personal

Disponible para todo usuario autenticado.

Descarga documentos personales emitidos por el usuario en la oficina seleccionada.

### Oficina

Disponible solo si el backend devuelve:

```json
"can_download_office": true
```

El backend considera jefe/oficina si cumple alguna condicion:

- `adm_esjefe` verdadero.
- Permiso `tramite.reporte.jefe`.
- Permiso `tramite.reporte.global`.
- Rol `JEFE`.

## Organizacion De Carpetas

La app agrupa archivos usando esta estructura:

```text
DESTINO/
  ANIO/
    TIPO_DOCUMENTO/
      RANGO/
        DOCUMENTO/
          archivo.pdf
```

Ejemplo:

```text
C:/cargos_sgd/2026/INFORME/000001-001000/INFORME 000001 GRH_GRI-WARAT/Documento principal Generado.pdf
```

El rango se calcula con el numero de documento cuando existe. Si no existe, usa `iddocumento`.

Con grupo `1000`:

```text
000001-001000
001001-002000
002001-003000
```

## Documentos Relacionados

Los relacionados se guardan dentro de la carpeta del documento principal. El nombre del archivo relacionado se prefija con el nombre del documento relacionado para evitar colisiones.

Ejemplo:

```text
MEMORANDUM 000001 GRH_GRI/
  MEMORANDUM 000001 GRH_GRI_Documento principal Generado.pdf
  INFORME 011315 GRH-GRI_SGGOS_11315.pdf.pdf
```

## Reintentos Y Omision De Archivos

La app no descarga de nuevo un archivo si ya existe localmente y:

- El backend no informa tamano, o
- El tamano local coincide con `file_size`.

Si el archivo no existe o el tamano no coincide, intenta descargarlo.

## Cancelacion

La cancelacion no interrumpe un archivo a media escritura. Marca la solicitud de parada y se detiene al terminar la operacion actual.

## Configuracion Local

La configuracion se guarda en:

```text
~/.sgd_cargos_downloader/config.json
```

Incluye:

- URL del servicio SGD.
- Carpeta destino.
- Tamano de grupo.
- Tamano de pagina.
- Incluir relacionados.
- Incluir personales dentro de alcance oficina.

La clave del usuario no se guarda.

## Consideraciones De Red

Si la app se ejecuta en Windows y el SGD esta publicado desde Docker en WSL, normalmente la URL sera:

```text
http://localhost:8079
```

Si el servicio esta en otro servidor, cambiar la URL en la interfaz.

La URL debe apuntar a la raiz del SGD, no directamente a `/api`.
