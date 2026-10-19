param(
  [switch]$KeepElectronZip
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ElectronVersion = '46.0.0-nightly.20261016'
$AppVersion = '0.1.30'
$ExpectedSha256 = $null
$ElectronFile = "electron-v$ElectronVersion-win32-x64.zip"
$ShasumsFile = 'SHASUMS256.txt'
$ElectronUrls = @(
  "https://github.com/electron/nightlies/releases/download/v$ElectronVersion/$ElectronFile",
  "https://npmmirror.com/mirrors/electron-nightly/$ElectronVersion/$ElectronFile"
)
$TargetName = "ChatGPT-Portable-Electron-$AppVersion-AuthFix-ChromiumNativeDragStateSeed-win-x64"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $ScriptRoot $TargetName
$Stage = Join-Path $env:TEMP ("ChatGPT-Portable-stage-" + [Guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $env:TEMP $ElectronFile
$ShasumsPath = Join-Path $env:TEMP ("electron-$ElectronVersion-SHASUMS256.txt")
$DataBackup = $null

function Get-Sha256Lower([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Download-TextFromSources([string[]]$Urls, [string]$OutFile) {
  $lastError = $null
  foreach ($url in $Urls) {
    try {
      Write-Host "      Fuente: $url"
      Invoke-WebRequest -Uri $url -OutFile $OutFile -UseBasicParsing
      return
    } catch {
      $lastError = $_.Exception.Message
      Remove-Item -LiteralPath $OutFile -Force -ErrorAction SilentlyContinue
    }
  }
  throw "No se pudo descargar desde ninguna fuente.`nUltimo error: $lastError"
}

function Get-ExpectedElectronHash {
  $sumUrls = @(
    "https://github.com/electron/nightlies/releases/download/v$ElectronVersion/$ShasumsFile",
    "https://npmmirror.com/mirrors/electron-nightly/$ElectronVersion/$ShasumsFile"
  )
  Download-TextFromSources $sumUrls $ShasumsPath
  $line = Get-Content -LiteralPath $ShasumsPath | Where-Object { $_ -match ([regex]::Escape($ElectronFile) + '$') } | Select-Object -First 1
  if (-not $line) { throw "SHASUMS256 no contiene $ElectronFile" }
  $hash = (($line -split '\s+')[0]).ToLowerInvariant()
  if ($hash -notmatch '^[0-9a-f]{64}$') { throw "SHA-256 invalido en SHASUMS256: $hash" }
  return $hash
}

function Download-Electron {
  $script:ExpectedSha256 = Get-ExpectedElectronHash
  Write-Host "[OK] SHA-256 oficial esperado: $ExpectedSha256"

  if (Test-Path -LiteralPath $ZipPath) {
    $existingHash = Get-Sha256Lower $ZipPath
    if ($existingHash -eq $ExpectedSha256) {
      Write-Host "[OK] Reutilizando runtime Electron verificado: $ZipPath"
      return
    }
    Remove-Item -LiteralPath $ZipPath -Force
  }

  Write-Host "[1/5] Descargando Electron $ElectronVersion / Chromium 158 para Windows x64..."
  Download-TextFromSources $ElectronUrls $ZipPath

  $hash = Get-Sha256Lower $ZipPath
  if ($hash -ne $ExpectedSha256) {
    Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ShasumsPath -Force -ErrorAction SilentlyContinue
    throw "Fallo de integridad. SHA-256 recibido: $hash ; esperado: $ExpectedSha256"
  }
  Write-Host "[OK] SHA-256 Electron verificado: $hash"
}

try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Download-Electron

  Write-Host "[2/5] Extrayendo runtime..."
  New-Item -ItemType Directory -Path $Stage -Force | Out-Null
  Expand-Archive -LiteralPath $ZipPath -DestinationPath $Stage -Force

  $electronExe = Join-Path $Stage 'electron.exe'
  if (-not (Test-Path -LiteralPath $electronExe)) {
    throw 'El paquete de Electron extraido no contiene electron.exe.'
  }


  # Native Chromium patch: preserve the working 0.1.25 DragEnter COPY fix,
  # then seed DropData::operation from source_operations & COPY at drag entry.
  # DesktopDropTargetWin::OnDragOver remains byte-identical to Electron.
  $originalExeSha = '5008929104e3514ecfe5975ea6baa31b68607e898e0b0236733fa388dfc6d61b'
  $patchedExeSha  = '717355b1e73100c8ef481607cf9831ac7deae47110b836b91729655750c8f48a'
  $enterOp = [Int64]0xA38EB2F
  $stateHook = [Int64]0x6F800A8
  $stateCave = [Int64]0x4191E80
  $stateHookOrig = [byte[]](0x4D,0x85,0xE4,0x74,0x15)
  $stateHookPatch = [byte[]](0xE9,0xD3,0x1D,0x21,0xFD)
  $stateCavePatch = [byte[]](
    0x41,0x8B,0x4E,0x10,0x83,0xE1,0x01,
    0x89,0x88,0x00,0x03,0x00,0x00,
    0x4D,0x85,0xE4,
    0x0F,0x84,0x2C,0xE2,0xDE,0x02,
    0xE9,0x12,0xE2,0xDE,0x02
  )
  $exeHashBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $electronExe).Hash.ToLowerInvariant()
  if ($exeHashBefore -ne $originalExeSha) { throw "electron.exe inesperado antes del parche nativo. SHA-256=$exeHashBefore" }
  $all = [IO.File]::ReadAllBytes($electronExe)
  if ($all[$enterOp] -ne 0x31 -or $all[$enterOp+1] -ne 0xC9) { throw 'Bytes OnDragEnter inesperados.' }
  for ($i=0; $i -lt $stateHookOrig.Length; $i++) { if ($all[$stateHook+$i] -ne $stateHookOrig[$i]) { throw 'Bytes DragEnteredCallback inesperados.' } }
  for ($i=0; $i -lt 64; $i++) { if ($all[$stateCave+$i] -ne 0xCC) { throw 'Code cave no esta limpia.' } }
  $all[$enterOp]=0xB1; $all[$enterOp+1]=0x01
  [Array]::Copy($stateHookPatch,0,$all,$stateHook,$stateHookPatch.Length)
  [Array]::Copy($stateCavePatch,0,$all,$stateCave,$stateCavePatch.Length)
  [IO.File]::WriteAllBytes($electronExe,$all)
  $exeHashAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $electronExe).Hash.ToLowerInvariant()
  if ($exeHashAfter -ne $patchedExeSha) { throw "SHA-256 inesperado despues del parche nativo: $exeHashAfter" }
  Write-Host "[OK] Chromium native DragStateSeed verificado: $exeHashAfter"

  Write-Host "[3/5] Integrando ChatGPT Portable..."
  Rename-Item -LiteralPath $electronExe -NewName 'ChatGPT Portable.exe'

  $resources = Join-Path $Stage 'resources'
  $defaultApp = Join-Path $resources 'default_app.asar'
  if (Test-Path -LiteralPath $defaultApp) {
    Remove-Item -LiteralPath $defaultApp -Force
  }

  $appTarget = Join-Path $resources 'app'
  if (Test-Path -LiteralPath $appTarget) {
    Remove-Item -LiteralPath $appTarget -Recurse -Force
  }
  Copy-Item -LiteralPath (Join-Path $ScriptRoot 'App') -Destination $appTarget -Recurse -Force

  $dataTarget = Join-Path $Stage 'Data'
  @('Profile','Session','Cache','Downloads','Logs','Crashes') | ForEach-Object {
    New-Item -ItemType Directory -Path (Join-Path $dataTarget $_) -Force | Out-Null
  }

  @"
ChatGPT Portable Electron $AppVersion
Electron $ElectronVersion / Windows x64

Ejecuta: ChatGPT Portable.exe
Datos portables: .\Data\
Descargas: .\Data\Downloads\

No usa Microsoft Edge WebView2. Electron incluye su propio Chromium.
El runtime Electron fue verificado antes de crear esta carpeta con SHA-256:
$ExpectedSha256
"@ | Set-Content -LiteralPath (Join-Path $Stage 'PORTABLE.txt') -Encoding UTF8

  Copy-Item -LiteralPath (Join-Path $ScriptRoot 'README.txt') -Destination (Join-Path $Stage 'README.txt') -Force
  Copy-Item -LiteralPath (Join-Path $ScriptRoot 'LICENSE-app.txt') -Destination (Join-Path $Stage 'LICENSE-app.txt') -Force

  Write-Host "[4/5] Publicando carpeta portable..."
  if (Test-Path -LiteralPath $Target) {
    $existingData = Join-Path $Target 'Data'
    if (Test-Path -LiteralPath $existingData) {
      $DataBackup = Join-Path $ScriptRoot ('.Data-preserve-' + [Guid]::NewGuid().ToString('N'))
      Move-Item -LiteralPath $existingData -Destination $DataBackup
      Write-Host '[OK] Perfil/sesion existentes preservados.'
    }
    Remove-Item -LiteralPath $Target -Recurse -Force
  }

  Move-Item -LiteralPath $Stage -Destination $Target

  if ($DataBackup -and (Test-Path -LiteralPath $DataBackup)) {
    $newData = Join-Path $Target 'Data'
    Remove-Item -LiteralPath $newData -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $DataBackup -Destination $newData
    $DataBackup = $null
  }

  Write-Host "[5/5] Verificacion final..."
  $finalExe = Join-Path $Target 'ChatGPT Portable.exe'
  $finalMain = Join-Path $Target 'resources\app\main.js'
  if (-not (Test-Path -LiteralPath $finalExe) -or -not (Test-Path -LiteralPath $finalMain)) {
    throw 'La carpeta final no paso la verificacion estructural.'
  }

  if (-not $KeepElectronZip) {
    Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
  }
  Remove-Item -LiteralPath $ShasumsPath -Force -ErrorAction SilentlyContinue

  Write-Host ''
  Write-Host '============================================================'
  Write-Host ' CHATGPT PORTABLE LISTO'
  Write-Host '============================================================'
  Write-Host "Carpeta: $Target"
  Write-Host "Ejecutable: $finalExe"
  Write-Host ''
  Write-Host 'Puedes mover la carpeta completa a cualquier ubicacion/unidad.'
  Write-Host 'No requiere instalacion ni WebView2.'
  Write-Host '============================================================'
} catch {
  if (Test-Path -LiteralPath $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
  }
  if ($DataBackup -and (Test-Path -LiteralPath $DataBackup)) {
    Write-Warning "Tus datos previos se conservaron aqui: $DataBackup"
  }
  Write-Host ''
  Write-Error $_
  exit 1
}
