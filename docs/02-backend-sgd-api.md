# API Requerida En SGD

## Ubicacion

Repositorio:

```text
/home/administrador/sgd-gore
```

Rutas:

```text
/home/administrador/sgd-gore/routes/api.php
```

Controlador:

```text
/home/administrador/sgd-gore/app/Http/Controllers/Api/CargoController.php
```

Middleware:

```text
/home/administrador/sgd-gore/app/Http/Middleware/CargoApiAuthenticate.php
```

Migracion:

```text
/home/administrador/sgd-gore/database/migrations/2026_08_28_000001_create_cargo_api_tokens_table.php
```

## Autenticacion

El backend no usa `auth:api` porque la base real no tenia columna `admin.api_token`, aunque el modelo `User` la documentaba. Para evitar alterar `admin`, se creo una tabla propia:

```text
cargo_api_tokens
```

El flujo es:

1. `POST /api/cargos/login` valida `adm_email` y `password`.
2. Si el usuario esta activo, vigente y completo su primer logeo, se genera un token aleatorio.
3. El token se guarda hasheado con SHA-256 en `cargo_api_tokens`.
4. El cliente recibe el token en texto plano solo una vez.
5. Las rutas protegidas usan:

```http
Authorization: Bearer TOKEN
```

6. `POST /api/cargos/logout` borra el token usado.

Los tokens expiran por defecto en 12 horas.

## Middleware

Middleware registrado en `app/Http/Kernel.php`:

```php
'cargo.api' => \App\Http\Middleware\CargoApiAuthenticate::class,
```

El middleware:

- Lee el token Bearer.
- Busca el hash en `cargo_api_tokens`.
- Verifica expiracion.
- Carga el usuario.
- Valida estado, vigencia y primer logeo.
- Establece el usuario en `Auth::setUser`.
- Guarda el ID del token en el request para permitir logout.

## Rutas Disponibles

Base URL configurable, por ejemplo:

```text
http://localhost:8079
```

### Login

```http
POST /api/cargos/login
Content-Type: application/json
Accept: application/json
```

Body:

```json
{
  "adm_email": "USUARIO",
  "password": "CLAVE"
}
```

Respuesta exitosa:

```json
{
  "token": "...",
  "expires_at": "2026-08-28 23:00:00",
  "user": {
    "id": 4,
    "adm_email": "WAGUIRRE",
    "depe_id": 45,
    "can_download_personal": true,
    "can_download_office": true,
    "offices": []
  }
}
```

Errores esperados:

- `401`: credenciales incorrectas.
- `403`: usuario inactivo, no vigente o primer logeo pendiente.
- `422`: payload invalido.

### Logout

```http
POST /api/cargos/logout
Authorization: Bearer TOKEN
```

Borra el token usado.

### Usuario Actual

```http
GET /api/cargos/me
Authorization: Bearer TOKEN
```

Devuelve datos del usuario, dependencia activa, permisos y oficinas disponibles.

### Oficinas Del Usuario

```http
GET /api/cargos/oficinas
Authorization: Bearer TOKEN
```

Devuelve oficinas activas desde `usuario_oficinas`. Si la oficina actual de `admin.depe_id` no esta en esa tabla, tambien se incluye como fallback.

### Documentos Emitidos

```http
GET /api/cargos/documentos
Authorization: Bearer TOKEN
```

Parametros:

```text
scope=personal|oficina
depe_id=45
fecha_desde=2026-01-01
fecha_hasta=2026-12-31
page=1
per_page=50
include_files=1
include_personal=0
with_total=0
```

Reglas:

- `scope=personal`: documentos personales emitidos por el usuario.
- `scope=oficina`: documentos emitidos por la oficina, solo si el usuario tiene permiso de jefe/oficina.
- `include_personal=1`: permite que el alcance oficina incluya tambien documentos personales emitidos dentro de la oficina.
- Por defecto usa `simplePaginate()` para evitar `count(*)` costoso.
- Si se necesita total exacto, enviar `with_total=1`.

Consulta base:

```text
tram_operacion.oper_idtope = 1
tram_operacion.oper_idprocesado IS NULL
tram_operacion.oper_iddependencia = depe_id
```

Para personal agrega:

```text
tram_operacion.oper_idusuario = usuario.id
tram_documento.docu_idusuario = usuario.id
tram_documento.docu_tipo = 1
```

Para oficina por defecto agrega:

```text
tram_documento.docu_tipo = 0
```

### Archivos De Documento

```http
GET /api/cargos/documentos/{documento}/archivos
Authorization: Bearer TOKEN
```

Parametros:

```text
scope=personal|oficina
depe_id=45
master_id=ID_DOCUMENTO_PRINCIPAL
```

`master_id` solo es necesario cuando se consultan archivos de un documento relacionado.

### Documentos Relacionados

```http
GET /api/cargos/documentos/{documento}/relacionados
Authorization: Bearer TOKEN
```

Busca documentos relacionados mediante:

```text
tram_operacion.oper_iddocumento_adj = documento_principal
```

Esto replica la logica principal del notebook original para ubicar cargos/adjuntos relacionados.

### Documentos Relacionados Por Lote

```http
POST /api/cargos/documentos/relacionados/batch
Authorization: Bearer TOKEN
Content-Type: application/json
Accept: application/json
```

Body:

```json
{
  "scope": "oficina",
  "depe_id": 45,
  "document_ids": [1001, 1002, 1003],
  "include_files": 1
}
```

Debe devolver los documentos relacionados de todos los IDs recibidos en un solo request, o en lotes definidos por el cliente. La app envia por defecto lotes de 200 documentos principales.

Formato recomendado:

```json
{
  "data": [
    {
      "master_id": 1001,
      "documents": []
    },
    {
      "master_id": 1002,
      "documents": []
    }
  ]
}
```

Tambien es aceptable devolver un objeto indexado por ID principal:

```json
{
  "data": {
    "1001": [],
    "1002": []
  }
}
```

Reglas:

- Validar que cada `document_id` sea accesible por el usuario con el mismo criterio del endpoint individual.
- Buscar relacionados mediante `tram_operacion.oper_iddocumento_adj IN (...)`.
- Incluir `files` cuando `include_files=1`, para que el cliente clasifique `Fisico` o `Digital` sin requests adicionales.
- Evitar un query por documento; resolver el lote con consultas `WHERE IN` y agrupar por documento principal.

### Descargar Archivo

```http
GET /api/cargos/archivos/{archivo}/download
Authorization: Bearer TOKEN
```

Parametros:

```text
scope=personal|oficina
depe_id=45
master_id=ID_DOCUMENTO_PRINCIPAL
```

La descarga:

- Verifica que el archivo exista en `tram_file`.
- Verifica que el documento sea accesible por el usuario.
- Para documentos relacionados, valida que el usuario tenga acceso al documento principal `master_id`.
- Lee desde `Storage::disk('tramite')`.
- Registra descarga en `log_files` con `motivo = 1` si la conexion de logs esta disponible.

Si el contenedor no tiene montado el storage de PDFs, puede responder:

```text
404 Archivo fisico no encontrado
```

Eso no implica error de permisos.

## Validaciones Realizadas

En Docker:

```text
php -l CargoController.php: OK
php -l CargoApiAuthenticate.php: OK
php artisan route:list --path=api/cargos: OK
migracion cargo_api_tokens: aplicada
```

HTTP probado:

```text
POST /api/cargos/login: OK
GET /api/cargos/me: OK
GET /api/cargos/oficinas: OK
GET /api/cargos/documentos scope personal: OK
GET /api/cargos/documentos scope oficina: OK
GET /api/cargos/documentos/{id}/archivos: OK
GET /api/cargos/documentos/{id}/relacionados: OK
POST /api/cargos/logout: OK
```

La prueba de descarga autorizada llego correctamente hasta storage y devolvio `404` porque no hay PDFs montados en ese contenedor.
