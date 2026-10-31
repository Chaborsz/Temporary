AOE2DE 101.103.54800.0 - P3O EXACT OVERLAY BRIDGE RC10

OBJETIVO
- Conservar el overlay/selector real del P3O migrado en RC3_FIXEDPOINT.
- NO recrear ni redibujar la UI.
- Sustituir unicamente el punto fijo (50,50) de RC3 por el Point-at-Mouse ya validado en 54800 justo antes de F12.

ARQUITECTURA
- version.dll = bridge RC10. Reenvia los 17 exports de version.dll a System32.
- P3OBackend.dll = version.dll exacto extraido de AoE2DE_P3O_VIKING_SAGAS_54800_MIGRATION_RC3_FIXEDPOINT.zip.
- AoE2DE_P3N.ini = catalogo/configuracion del RC3.
- Insert, dibujo del overlay, clicks, busqueda, categorias, seleccion, lifecycle y shutdown pertenecen al backend RC3 y no son reimplementados por RC10.

PREPARACION
1. Cierra AoE2DE.
2. Extrae este paquete en la carpeta de AoE2DE_s.exe. El version.dll de este paquete debe quedar como version.dll.
3. Copia junto a MAKE_BACKEND_FROM_RC3.cmd el archivo exacto:
   AoE2DE_P3O_VIKING_SAGAS_54800_MIGRATION_RC3_FIXEDPOINT.zip
4. Ejecuta MAKE_BACKEND_FROM_RC3.cmd.
5. Deben existir junto a AoE2DE_s.exe:
   version.dll
   P3OBackend.dll
   AoE2DE_P3N.ini

PRUEBA
- Entra en partida.
- Verifica que el overlay es el del backend antiguo, no el overlay Win32 reconstruido de RC9 FIX3.
- Verifica Insert.
- Verifica las 7 categorias y el catalogo.
- F12 debe spawnear bajo el mouse.
- Prueba varios puntos y zoom 1.0 / zoom in / zoom out.
- Sal al menu y luego cierra el juego; el proceso debe morir naturalmente.

DIAGNOSTICO
Si F12 no spawnea bajo el mouse o el bridge no se engancha, envia:
%TEMP%\AoE2DE_P3O_54800_EXACT_OVERLAY_BRIDGE_RC10.log

NOTA
RC10 no es Stable hasta completar la validacion runtime anterior.
