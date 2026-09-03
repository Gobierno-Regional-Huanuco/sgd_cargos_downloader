<#
.SYNOPSIS
    Prueba de conectividad manual contra el backend SGD (login + rutas /api/cargos).

.DESCRIPTION
    Hace login y llama GET /api/cargos/me, GET /api/cargos/oficinas y, si se indica
    -DepeId, GET /api/cargos/documentos con el scope/periodo indicados. Imprime codigo
    HTTP, tiempo de respuesta y cuerpo de cada paso, y cierra sesion al final.
    Sirve para comparar el comportamiento del SGD entre el ambiente local y el
    publicado cuando la aplicacion falla (ver docs/pruebas-conexion-sgd.md).

.EXAMPLE
    .\scripts\test_sgd_connection.ps1 -ServiceUrl "https://digital.regionhuanuco.gob.pe/" -Scope personal -DepeId 45 -Period 2025

.EXAMPLE
    .\scripts\test_sgd_connection.ps1 -ServiceUrl "http://localhost:8079"
#>

param(
    [string]$ServiceUrl = "",
    [string]$Username = "",
    [string]$Password = "",
    [string]$Scope = "personal",
    [int]$DepeId = 0,
    [int]$Period = (Get-Date).Year
)

# ---- Editar aca si preferis no pasar parametros cada vez ----
if (-not $ServiceUrl) { $ServiceUrl = "https://digital.regionhuanuco.gob.pe/" }
if (-not $Username)   { $Username = "" }   # ej: "waguirre"; si queda vacio se pide interactivo
if (-not $Password)   { $Password = "" }   # dejar vacio: se pide oculto, no queda en el archivo
# ---------------------------------------------------------------

$ErrorActionPreference = "Stop"
$ServiceUrl = $ServiceUrl.TrimEnd("/") + "/"

if (-not $Username) {
    $Username = Read-Host "Usuario SGD"
}
if (-not $Password) {
    $securePassword = Read-Host "Clave SGD" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

function Invoke-SgdRequest {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [string]$Body = ""
    )
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        if ($Body) {
            $response = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -Body $Body -ContentType "application/json" -UseBasicParsing
        } else {
            $response = Invoke-WebRequest -Uri $Uri -Method $Method -Headers $Headers -UseBasicParsing
        }
        $sw.Stop()
        return [pscustomobject]@{ StatusCode = [int]$response.StatusCode; Content = $response.Content; Ms = $sw.ElapsedMilliseconds }
    } catch {
        $sw.Stop()
        $resp = $_.Exception.Response
        if ($resp) {
            $stream = $resp.GetResponseStream()
            $reader = New-Object IO.StreamReader($stream)
            $content = $reader.ReadToEnd()
            return [pscustomobject]@{ StatusCode = [int]$resp.StatusCode; Content = $content; Ms = $sw.ElapsedMilliseconds }
        }
        return [pscustomobject]@{ StatusCode = -1; Content = "Error de conexion: $($_.Exception.Message)"; Ms = $sw.ElapsedMilliseconds }
    }
}

function Write-Step {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Show-Result {
    param($Result)
    $color = if ($Result.StatusCode -ge 200 -and $Result.StatusCode -lt 300) { "Green" } else { "Red" }
    Write-Host "Status: $($Result.StatusCode)  ($($Result.Ms) ms)" -ForegroundColor $color
    Write-Host $Result.Content
}

$loginUrl = "${ServiceUrl}api/cargos/login"
Write-Step "POST $loginUrl"
$loginBody = @{ adm_email = $Username; password = $Password } | ConvertTo-Json
$login = Invoke-SgdRequest -Method Post -Uri $loginUrl -Headers @{ Accept = "application/json" } -Body $loginBody
Show-Result $login

if ($login.StatusCode -lt 200 -or $login.StatusCode -ge 300) {
    Write-Host ""
    Write-Host "Login fallido, no se puede continuar." -ForegroundColor Red
    exit 1
}

$token = $null
try { $token = ($login.Content | ConvertFrom-Json).token } catch {}
if (-not $token) {
    Write-Host ""
    Write-Host "La respuesta no trajo 'token'." -ForegroundColor Red
    exit 1
}
$authHeaders = @{ Accept = "application/json"; Authorization = "Bearer $token" }

$meUrl = "${ServiceUrl}api/cargos/me"
Write-Step "GET $meUrl"
Show-Result (Invoke-SgdRequest -Method Get -Uri $meUrl -Headers $authHeaders)

$officesUrl = "${ServiceUrl}api/cargos/oficinas"
Write-Step "GET $officesUrl"
Show-Result (Invoke-SgdRequest -Method Get -Uri $officesUrl -Headers $authHeaders)

if ($DepeId -gt 0) {
    $fechaDesde = "$Period-01-01"
    $fechaHasta = "$Period-12-31"
    $docsUrl = "${ServiceUrl}api/cargos/documentos?scope=$Scope&depe_id=$DepeId&page=1&per_page=5&include_files=0&fecha_desde=$fechaDesde&fecha_hasta=$fechaHasta&with_total=1"
    Write-Step "GET $docsUrl"
    Show-Result (Invoke-SgdRequest -Method Get -Uri $docsUrl -Headers $authHeaders)
} else {
    Write-Host ""
    Write-Host "Sugerencia: pasa -DepeId <numero> (y opcionalmente -Scope/-Period) para probar la ruta de documentos." -ForegroundColor Yellow
}

$logoutUrl = "${ServiceUrl}api/cargos/logout"
Write-Step "POST $logoutUrl"
Show-Result (Invoke-SgdRequest -Method Post -Uri $logoutUrl -Headers $authHeaders)
