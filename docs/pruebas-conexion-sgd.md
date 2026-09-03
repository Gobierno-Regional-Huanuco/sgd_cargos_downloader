# Pruebas De Conexion Al SGD

## Alcance

Esta guia sirve para diagnosticar, desde afuera de la aplicacion, si el backend
SGD esta respondiendo el contrato descrito en [api.md](api.md). Sirve para
comparar el comportamiento entre el ambiente local y el publicado cuando la
aplicacion falla con `No autenticado` u otro error sin causa clara en la
interfaz.

## Scripts Listos

- PowerShell: `scripts/test_sgd_connection.ps1`
- Bash / Git Bash / WSL: `scripts/test_sgd_connection.sh`

Ambos hacen login, `GET /api/cargos/me`, `GET /api/cargos/oficinas` y, si se
indica `depe_id`, `GET /api/cargos/documentos`; imprimen codigo HTTP, tiempo de
respuesta y cuerpo de cada paso, y cierran sesion al final.

```powershell
.\scripts\test_sgd_connection.ps1 -ServiceUrl "https://digital.regionhuanuco.gob.pe/" -Scope personal -DepeId 45 -Period 2025
```

```bash
SGD_URL="https://digital.regionhuanuco.gob.pe/" ./scripts/test_sgd_connection.sh personal 45 2025
```

Las credenciales se piden de forma interactiva y oculta si no se pasan por
parametro (`-Username`/`-Password` en PowerShell) o variable de entorno
(`SGD_USER`/`SGD_PASS` en bash). No quedan escritas en el archivo salvo que se
editen a proposito en la seccion marcada al inicio de cada script.

## Peticiones Manuales (curl / Postman)

Reemplazar `<URL>`, `<USUARIO>`, `<CLAVE>`, `<TOKEN>`, `<DEPE_ID>` y
`<PERIODO>` antes de ejecutar. `<URL>` termina en `/`, por ejemplo
`https://digital.regionhuanuco.gob.pe/` o `http://localhost:8079/`.

### 1. Login

```bash
curl -i -X POST "<URL>api/cargos/login" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"adm_email":"<USUARIO>","password":"<CLAVE>"}'
```

Postman: `POST <URL>api/cargos/login`, header `Accept: application/json`,
cuerpo `raw` tipo `JSON`:

```json
{
  "adm_email": "<USUARIO>",
  "password": "<CLAVE>"
}
```

Copiar el campo `token` de la respuesta para los pasos siguientes.

### 2. Identidad

```bash
curl -i "<URL>api/cargos/me" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <TOKEN>"
```

### 3. Oficinas autorizadas

```bash
curl -i "<URL>api/cargos/oficinas" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Documentos (la ruta que suele fallar)

```bash
curl -i "<URL>api/cargos/documentos?scope=personal&depe_id=<DEPE_ID>&page=1&per_page=5&include_files=0&fecha_desde=<PERIODO>-01-01&fecha_hasta=<PERIODO>-12-31&with_total=1" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <TOKEN>"
```

Repetir cambiando `scope=personal` por `scope=oficina` para comparar.

### 5. Logout

```bash
curl -i -X POST "<URL>api/cargos/logout" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer <TOKEN>"
```

## Que Comparar

- Correr la misma secuencia con el mismo usuario y `depe_id` contra la URL
  local (por ejemplo `http://localhost:8079/`) y contra la publicada, y
  comparar codigo HTTP y cuerpo de cada paso.
- Un `401 {"message":"Unauthenticated."}` en `documentos` con un login `200`
  valido indica que el guard de esa ruta especifica esta rechazando el token,
  no que la clave sea incorrecta.
- Si `scope=oficina` tambien falla con el mismo `depe_id`, el problema no es de
  permisos por alcance ni por periodo: es una falla general del guard de
  `/api/cargos/*` en ese ambiente, y corresponde reportarlo a quien administra
  el backend SGD.
- Guardar el `Id. de informe`/timestamp de la prueba si se va a reportar: el
  backend suele loguear por horario y usuario.
