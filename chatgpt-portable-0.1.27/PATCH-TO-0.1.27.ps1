param([Parameter(Mandatory=$true)][string]$PortablePath)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$src=Join-Path $here 'App'
$dst=Join-Path $PortablePath 'resources\app'
$exe=Join-Path $PortablePath 'ChatGPT Portable.exe'
$original='5008929104e3514ecfe5975ea6baa31b68607e898e0b0236733fa388dfc6d61b'
$p125='5ef1227723cacd884b433e34589c2b63fd70bb30753cad18c0a60344dde6aa88'
$p126='a34d64d7af007b1a1068bc7694f86c0023d247c0f2a2dd8888d8c0eeddee4e6f'
$final='0c9be9f4d51978180afe65907401a6ee36f169b0615e99a36766287a2de7c8c8'
$entry=0xA38EAE0
$old=0xA38EB2F
$upd=0x6F80B70
function HexRange([byte[]]$b,[int]$o,[int]$n){(($b[$o..($o+$n-1)]|ForEach-Object{$_.ToString('X2')}) -join ' ')}
if(!(Test-Path $dst -PathType Container)){throw 'resources\app ausente'}
if(!(Test-Path $exe -PathType Leaf)){throw 'EXE ausente'}
$sha=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "SHA actual: $sha"
if($sha -ne $final){
 if($sha -ne $original -and $sha -ne $p125 -and $sha -ne $p126){throw "Runtime no reconocido: $sha"}
 $all=[IO.File]::ReadAllBytes($exe)
 if((HexRange $all $upd 6) -ne '8B 98 00 03 00 00'){throw "OnDragUpdated bytes inesperados: $(HexRange $all $upd 6)"}
 $f=[IO.File]::Open($exe,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 try{
  [void]$f.Seek($entry,[IO.SeekOrigin]::Begin);$x=[byte[]](0x56,0x57,0x48,0x83,0xEC);$f.Write($x,0,$x.Length)
  [void]$f.Seek($old,[IO.SeekOrigin]::Begin);$x=[byte[]](0x31,0xC9);$f.Write($x,0,$x.Length)
  [void]$f.Seek($upd,[IO.SeekOrigin]::Begin);$x=[byte[]](0x44,0x89,0xF3,0x83,0xE3,0x01);$f.Write($x,0,$x.Length)
  $f.Flush($true)
 }finally{$f.Dispose()}
 $sha=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
 if($sha -ne $final){throw "SHA final inesperado: $sha"}
}
foreach($n in @('main.js','preload.js','package.json')){Copy-Item (Join-Path $src $n) (Join-Path $dst $n) -Force}
if(!(Get-Content (Join-Path $dst 'main.js') -Raw).Contains("const APP_VERSION = '0.1.27';")){throw 'main marker'}
$p=Get-Content (Join-Path $dst 'preload.js') -Raw
if(!$p.Contains('preload-native-chromium-drop-v5-native-dragover-sync-installed')){throw 'preload marker'}
if($p.Contains('preventDefault') -or $p.Contains("dropEffect = 'copy'") -or $p.Contains('stopImmediatePropagation')){throw 'preload no pasivo'}
$j=Get-Content (Join-Path $dst 'package.json') -Raw|ConvertFrom-Json
if($j.version -ne '0.1.27'){throw 'package version'}
Write-Host '[OK] 0.1.27 aplicado y verificado.'
