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
$patch0125Sha   = '5ef1227723cacd884b433e34589c2b63fd70bb30753cad18c0a60344dde6aa88'
$patchedExeSha  = 'a34d64d7af007b1a1068bc7694f86c0023d247c0f2a2dd8888d8c0eeddee4e6f'
$entryOffset = [Int64]0xA38EAE0
$oldPatchOffset = [Int64]0xA38EB2F

function Write-Bytes([System.IO.FileStream]$fs, [Int64]$offset, [byte[]]$bytes) {
  [void]$fs.Seek($offset, [System.IO.SeekOrigin]::Begin)
  $fs.Write($bytes,0,$bytes.Length)
}
function Read-Bytes([System.IO.FileStream]$fs, [Int64]$offset, [int]$count) {
  [void]$fs.Seek($offset, [System.IO.SeekOrigin]::Begin)
  $buf = New-Object byte[] $count
  $n = $fs.Read($buf,0,$count)
  if ($n -ne $count) { throw 'No se pudieron leer los bytes esperados del EXE.' }
  return $buf
}
function Hex([byte[]]$b) { return (($b | ForEach-Object { $_.ToString('X2') }) -join ' ') }

Write-Host "Objetivo: $PortablePath"
if (-not (Test-Path -LiteralPath $dst -PathType Container)) { throw "No se encontro resources\app en: $PortablePath" }
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "No se encontro ChatGPT Portable.exe en: $PortablePath" }
$currentSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
Write-Host "SHA-256 actual EXE: $currentSha"

if ($currentSha -eq $patchedExeSha) {
  Write-Host '[OK] Parche nativo 0.1.26 ya aplicado.'
} elseif ($currentSha -eq $originalExeSha -or $currentSha -eq $patch0125Sha) {
  $fs = [System.IO.File]::Open($exe,[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
  try {
    $entry = Read-Bytes $fs $entryOffset 5
    if ((Hex $entry) -ne '56 57 48 83 EC') { throw ("Bytes inesperados en OnDragEnter: {0}" -f (Hex $entry)) }
    $old = Read-Bytes $fs $oldPatchOffset 2
    if ($currentSha -eq $originalExeSha) {
      if ((Hex $old) -ne '31 C9') { throw ("Bytes inesperados en parche 0.1.25: {0}" -f (Hex $old)) }
    } else {
      if ((Hex $old) -ne 'B1 01') { throw ("Runtime 0.1.25 reconocido por SHA pero bytes inesperados: {0}" -f (Hex $old)) }
    }
    Write-Host 'Aplicando salto nativo OnDragEnter -> OnDragOver...'
    Write-Bytes $fs $entryOffset ([byte[]](0xE9,0xFB,0x02,0x00,0x00))
    Write-Bytes $fs $oldPatchOffset ([byte[]](0x31,0xC9))
    $fs.Flush($true)
  } finally { $fs.Dispose() }
  $afterSha=(Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
  if ($afterSha -ne $patchedExeSha) { throw "SHA-256 inesperado despues del parche: $afterSha" }
  Write-Host "[OK] EXE nativo 0.1.26 verificado: $afterSha"
} else {
  throw "Runtime no reconocido. No se modifico el EXE. SHA-256=$currentSha"
}

Write-Host 'Instalando App 0.1.26 con trazas pasivas...'
foreach ($name in @('main.js','preload.js','package.json')) {
  $source=Join-Path $src $name
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Falta archivo: $source" }
  Copy-Item -LiteralPath $source -Destination (Join-Path $dst $name) -Force
}
$mainText=Get-Content -LiteralPath (Join-Path $dst 'main.js') -Raw
if (-not $mainText.Contains("const APP_VERSION = '0.1.26';")) { throw 'APP_VERSION no es 0.1.26.' }
$preloadText=Get-Content -LiteralPath (Join-Path $dst 'preload.js') -Raw
if (-not $preloadText.Contains('preload-native-chromium-drop-v4-native-dragenter-delegate-installed')) { throw 'Marker preload 0.1.26 ausente.' }
if ($preloadText.Contains('event.preventDefault()') -or $preloadText.Contains("dropEffect = 'copy'") -or $preloadText.Contains('stopImmediatePropagation')) { throw 'Preload no es pasivo.' }
$json=Get-Content -LiteralPath (Join-Path $dst 'package.json') -Raw | ConvertFrom-Json
if ($json.version -ne '0.1.26') { throw "package.json version=$($json.version)" }
$finalSha=(Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
if ($finalSha -ne $patchedExeSha) { throw "Verificacion final EXE fallo: $finalSha" }
Write-Host '[OK] Hotfix 0.1.26 aplicado y verificado.'
Write-Host '[OK] OnDragEnter usa la ruta OnDragOver/OnDragUpdated nativa.'
Write-Host 'Data y sesion no fueron modificados.'
exit 0
