# Desarrollo Y Empaquetado En Windows

## Recomendacion

Para probar la GUI y generar `.exe`, usar Windows directamente. No copiar el venv de WSL.

Copiar la carpeta:

```text
~/cargos_downloader
```

a una ruta de Windows, por ejemplo:

```text
C:\dev\cargos_downloader
```

## Crear Venv En Windows

En PowerShell:

```powershell
cd C:\dev\cargos_downloader
py -3 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecutar En Desarrollo

```powershell
$env:PYTHONPATH="src"
python -m cargos_downloader.main
```

## Configurar URL SGD

Si el SGD corre en Docker/WSL y publica el puerto:

```text
8079 -> 80
```

usar:

```text
http://localhost:8079
```

Si Windows no llega a esa URL, revisar:

```powershell
curl http://localhost:8079
```

Debe responder la pantalla de login del SGD o una redireccion a `/login`.

## Empaquetar EXE

Desde PowerShell:

```powershell
cd C:\dev\cargos_downloader
.\scripts\build_windows.ps1
```

Salida esperada:

```text
dist\SGD-Cargos-Downloader.exe
```

## Problemas Comunes

### `ModuleNotFoundError: No module named PySide6`

El venv no tiene dependencias o se activo un venv incorrecto.

Solucion:

```powershell
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### `python` No Existe

En Windows usar:

```powershell
py -3
```

o instalar Python desde python.org marcando "Add Python to PATH".

### La App Abre Pero No Login

Verificar:

- URL correcta del SGD.
- Que `/api/cargos/login` exista en el backend.
- Que la migracion `cargo_api_tokens` este aplicada.
- Que el usuario este activo, vigente y con primer logeo completo.

### Descarga Devuelve 404

Si la consulta de documentos funciona pero la descarga devuelve 404, probablemente el backend no tiene montado el storage de PDFs.

Validar en SGD:

```text
Storage::disk('tramite')
```

y la variable de entorno:

```text
PATH_TRAMITE
```

## Validacion Minima Antes De Entregar

1. Login exitoso.
2. Carga oficinas.
3. Lista documentos personales.
4. Lista documentos de oficina para jefe.
5. Descarga un archivo real.
6. Cierra sesion sin dejar token activo.
7. Genera `.exe`.
8. Ejecuta el `.exe` en una maquina limpia de prueba.
