param(
  [Parameter(Mandatory=$true)][string]$PortablePath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $here 'App'
$dst = Join-Path $PortablePath 'resources\app'
$exe = Join-Path $PortablePath 'ChatGPT Portable.exe'
$originalExeSha = '5008929104e3514ecfe5975ea6baa31b68607e898e0b0236733fa388dfc6d61b'
$patchedExeSha  = '5ef1227723cacd884b433e34589c2b63fd70bb30753cad18c0a60344dde6aa88'
$patchOffset = [Int64]0xA38EB2F

Write-Host "Objetivo: $PortablePath"
Write-Host 'Verificando runtime Electron/Chromium exacto...'
if (-not (Test-Path -LiteralPath $dst -PathType Container)) { throw "No se encontro resources\app en: $PortablePath" }
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "No se encontro ChatGPT Portable.exe en: $PortablePath" }
$currentSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
Write-Host "SHA-256 actual EXE: $currentSha"

if ($currentSha -eq $patchedExeSha) {
  Write-Host '[OK] El parche nativo del EXE ya estaba aplicado.'
} elseif ($currentSha -eq $originalExeSha) {
  $fs = [System.IO.File]::Open($exe, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
  try {
    [void]$fs.Seek($patchOffset, [System.IO.SeekOrigin]::Begin)
    $b0 = $fs.ReadByte(); $b1 = $fs.ReadByte()
    if ($b0 -ne 0x31 -or $b1 -ne 0xC9) { throw ("Bytes inesperados en offset 0x{0:X}: {1:X2} {2:X2}; esperado 31 C9." -f $patchOffset,$b0,$b1) }
    Write-Host 'Aplicando parche nativo Chromium: 31 C9 -> B1 01...'
    [void]$fs.Seek($patchOffset, [System.IO.SeekOrigin]::Begin)
    $fs.WriteByte(0xB1); $fs.WriteByte(0x01); $fs.Flush($true)
  } finally { $fs.Dispose() }
  $afterSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
  if ($afterSha -ne $patchedExeSha) {
    $restore = [System.IO.File]::Open($exe, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    try {
      [void]$restore.Seek($patchOffset, [System.IO.SeekOrigin]::Begin)
      $restore.WriteByte(0x31); $restore.WriteByte(0xC9); $restore.Flush($true)
    } finally { $restore.Dispose() }
    throw "SHA-256 inesperado despues del parche: $afterSha. Bytes restaurados."
  }
  Write-Host "[OK] EXE nativo parcheado y verificado: $afterSha"
} else {
  throw "Runtime no reconocido. No se modifico el EXE. SHA-256=$currentSha"
}

Write-Host 'Instalando App 0.1.25 con trazas pasivas...'
foreach ($name in @('main.js','preload.js','package.json')) {
  $source = Join-Path $src $name
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Falta archivo del hotfix: $source" }
  Copy-Item -LiteralPath $source -Destination (Join-Path $dst $name) -Force
}
$mainText = Get-Content -LiteralPath (Join-Path $dst 'main.js') -Raw
if (-not $mainText.Contains("const APP_VERSION = '0.1.25';")) { throw 'Verificacion fallida: APP_VERSION no es 0.1.25.' }
$preloadText = Get-Content -LiteralPath (Join-Path $dst 'preload.js') -Raw
if (-not $preloadText.Contains('preload-native-chromium-drop-v3-native-runtime-patch-installed')) { throw 'Verificacion fallida: marker de preload 0.1.25 ausente.' }
if ($preloadText.Contains('event.preventDefault()') -or $preloadText.Contains("dropEffect = 'copy'") -or $preloadText.Contains('stopImmediatePropagation')) { throw 'Verificacion fallida: preload no es pasivo.' }
$json = Get-Content -LiteralPath (Join-Path $dst 'package.json') -Raw | ConvertFrom-Json
if ($json.version -ne '0.1.25') { throw "Verificacion fallida: package.json version=$($json.version)" }
$finalSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
if ($finalSha -ne $patchedExeSha) { throw "Verificacion final del EXE fallo: $finalSha" }
Write-Host '[OK] Hotfix 0.1.25 aplicado y verificado.'
Write-Host '[OK] Runtime nativo + App + preload pasivo: PASS.'
Write-Host 'Data y sesion no fueron modificados.'
exit 0
