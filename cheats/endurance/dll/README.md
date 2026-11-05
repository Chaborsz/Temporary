# Endurance 2047 — DLL experimental de 32 bits

**Estado: experimental; sin validacion de jugabilidad.** La DLL modifica de forma transitoria las asignaciones de la variable global 2047 (medidor de tentacion/excitacion) durante el juego. No cambia player.exe, project.json, HP, MP, 2003, 2054 ni 2386.

## Uso (Windows 10/11)

1. Deja el project.json original del juego en Resources\data\project.json (si aplicaste la build Stage9, restauralo antes).
2. Cierra el juego y guarda una copia de sus partidas.
3. Comprueba que no existe ya un fichero version.dll junto a player.exe; **si existe, no lo sobrescribas** porque podria pertenecer a otro mod.
4. Descarga el artefacto SUCCESS de https://github.com/Chaborsz/Temporary/actions/workflows/endurance-dll-build.yml.
5. Copia **solo version.dll** a la misma carpeta de player.exe, nunca a System32.
6. Inicia el juego. Consulta Endurance2047.log junto a version.dll:
   - SOURCE_OK: hash SHA256 del player.exe original verificado;
   - HOOK_INSTALLED: el filtro de asignaciones 2047 se activo;
   - GUARD_FAIL: el ejecutable difiere del canonical; la DLL solo retransmite los servicios de Windows;
   - HOOK_FAILED: se rechazo la modificacion para evitar un posible fallo.
7. Comprueba en una partida temporal si el medidor bajo HP/MP deja de subir al recibir tentacion. Comprueba la estabilidad del HUD y eventos.
8. Para desinstalar, cierra el juego y **elimina version.dll** de la carpeta del juego. Reinicia.

## Detalles tecnicos

- Es un proxy VERSION.dll de x86 (el player.exe importa esta biblioteca de Windows).
- Reenvia diez funciones de version Windows a System32\version.dll.
- Solo intenta activar el filtro si el ejecutable tiene exactamente 8.757.760 bytes y SHA256 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea.
- La direccion del punto de intercepcion es RVA 0x1E8760 (GameManager::assignVariableData) y su prologo tiene validacion binaria de seis bytes.
- Identificador de PlayVariableData en +0x18; puntero a objeto en +0x60; solo intercepta ID2047 sin objeto asociado.
- Sustituye el operador de asignacion por 0 (asignar) y valor por 0.0. No se modifica el codigo de otros setters ni archivos de datos.
- El filtro es dinamico y no necesita que el contenido completo del project.json se distribuya en el artefacto.

## Limitaciones y seguridad

- **Esta DLL NO ha sido ejecutada dentro de Forest of the Blue Skin.** Las pruebas automaticas solo verifican arquitectura PE32, integridad del EXE, exportaciones, compatibilidad proxy y compilacion.
- Podria no interceptar rutas que no utilicen GameManager::assignVariableData.
- El guardado puede restaurar valores hasta que el juego ejecute una asignacion.
- Ciertas escenas dependen de la tentacion (75/76): mantenerla a 0 podria bloquear su avance.
- No usar en juegos online ni junto a otros proxies version.dll, ni junto con el project.json modificado de Stage9.
- Si la DLL no carga o causa errores, desinstalarla y restaurar los ficheros originales. La desinstalacion no modifica datos en disco.
- El archivo Endurance2047.log se crea solo en la carpeta del propio juego, no se envia a ningun servidor.

Fuente: cheats/endurance/dll/endurance2047_version.cpp; manifest de resultados disponible en GitHub Actions.
