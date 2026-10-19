param([Parameter(Mandatory=$true)][string]$PortablePath)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$src=Join-Path $here 'App'
$dst=Join-Path $PortablePath 'resources\app'
$exe=Join-Path $PortablePath 'ChatGPT Portable.exe'
$known=@(
 '5008929104e3514ecfe5975ea6baa31b68607e898e0b0236733fa388dfc6d61b',
 '5ef1227723cacd884b433e34589c2b63fd70bb30753cad18c0a60344dde6aa88',
 'a34d64d7af007b1a1068bc7694f86c0023d247c0f2a2dd8888d8c0eeddee4e6f',
 '0c9be9f4d51978180afe65907401a6ee36f169b0615e99a36766287a2de7c8c8',
 'd65be021ea56ff04228ee0780e7685cbe67db838cd7c331294729f641b07591f',
 'e62e5092c8650c2029d7fbc78ed09fbd2bb9f94ad6632d52b988b3f22b49f657'
)
$final='717355b1e73100c8ef481607cf9831ac7deae47110b836b91729655750c8f48a'
$entry=[Int64]0xA38EAE0
$enterOp=[Int64]0xA38EB2F
$update=[Int64]0x6F80B70
$overHook=[Int64]0xA38EE63
$overConv=[Int64]0xA38EE6D
$cave1=[Int64]0xA38E710
$cave2=[Int64]0xA3924B0
$stateHook=[Int64]0x6F800A8
$stateCave=[Int64]0x4191E80
function Put([byte[]]$all,[Int64]$o,[byte[]]$v){[Array]::Copy($v,0,$all,$o,$v.Length)}
function HexAt([byte[]]$all,[Int64]$o,[int]$n){ (($all[$o..($o+$n-1)] | ForEach-Object {$_.ToString('X2')}) -join ' ') }
if(!(Test-Path $dst -PathType Container)){throw 'resources\app ausente'}
if(!(Test-Path $exe -PathType Leaf)){throw 'ChatGPT Portable.exe ausente'}
$sha=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Runtime SHA actual: $sha"
if($sha -ne $final){
 if($known -notcontains $sha){throw "Runtime no reconocido: $sha"}
 $b=[IO.File]::ReadAllBytes($exe)
 Put $b $entry ([byte[]](0x56,0x57,0x48,0x83,0xEC))
 Put $b $enterOp ([byte[]](0x31,0xC9))
 Put $b $update ([byte[]](0x8B,0x98,0x00,0x03,0x00,0x00))
 Put $b $overHook ([byte[]](0x48,0x8D,0x4C,0x24,0x50))
 Put $b $overConv ([byte[]](0x89,0xF1,0xE8,0x1C,0x07,0x00,0x00,0x89,0xC6))
 Put $b $cave1 ([byte[]](0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC))
 Put $b $cave2 ([byte[]](0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC))
 Put $b $stateHook ([byte[]](0x4D,0x85,0xE4,0x74,0x15))
 Put $b $stateCave ([byte[]](0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,
                            0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,
                            0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,
                            0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC,0xCC))
 Put $b $enterOp ([byte[]](0xB1,0x01))
 Put $b $stateHook ([byte[]](0xE9,0xD3,0x1D,0x21,0xFD))
 Put $b $stateCave ([byte[]](0x41,0x8B,0x4E,0x10,0x83,0xE1,0x01,0x89,0x88,0x00,0x03,0x00,0x00,0x4D,0x85,0xE4,
                            0x0F,0x84,0x2C,0xE2,0xDE,0x02,0xE9,0x12,0xE2,0xDE,0x02))
 [IO.File]::WriteAllBytes($exe,$b)
 $sha=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
 if($sha -ne $final){throw "SHA final inesperado: $sha"}
}
$b=[IO.File]::ReadAllBytes($exe)
if((HexAt $b $enterOp 2) -ne 'B1 01'){throw 'OnDragEnter 0.1.25 ausente'}
if((HexAt $b $stateHook 5) -ne 'E9 D3 1D 21 FD'){throw 'DragEnteredCallback hook ausente'}
if((HexAt $b $stateCave 27) -ne '41 8B 4E 10 83 E1 01 89 88 00 03 00 00 4D 85 E4 0F 84 2C E2 DE 02 E9 12 E2 DE 02'){throw 'DragStateSeed cave incorrecta'}
if((HexAt $b $overHook 5) -ne '48 8D 4C 24 50'){throw 'OnDragOver no fue restaurado'}
if((HexAt $b $overConv 9) -ne '89 F1 E8 1C 07 00 00 89 C6'){throw 'OnDragOver conversion no fue restaurada'}
foreach($n in @('main.js','preload.js','package.json')){Copy-Item (Join-Path $src $n) (Join-Path $dst $n) -Force}
if(!(Get-Content (Join-Path $dst 'main.js') -Raw).Contains("const APP_VERSION = '0.1.30';")){throw 'main marker'}
$p=Get-Content (Join-Path $dst 'preload.js') -Raw
if(!$p.Contains('preload-native-chromium-drop-v8-current-drag-state-seed-installed')){throw 'preload marker'}
if($p.Contains('preventDefault') -or $p.Contains("dropEffect = 'copy'") -or $p.Contains('stopImmediatePropagation')){throw 'preload no pasivo'}
$j=Get-Content (Join-Path $dst 'package.json') -Raw|ConvertFrom-Json
if($j.version -ne '0.1.30'){throw 'package version'}
Write-Host '[OK] 0.1.30 aplicado y verificado.'
Write-Host "Runtime SHA: $final"
