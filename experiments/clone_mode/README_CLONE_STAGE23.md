# Endurance + Clone Mode Stage23 — prueba experimental x86

**Estado:** build experimental; NO se ha ejecutado en una partida real.
Conserva el cheat Endurance Stage13 que el usuario confirmo funcional.

## Controles
- Ctrl+Mayus+F9: crear una segunda instancia del objeto jugable ID1 (プレイヤー) al lado
  del jugador actual (56 px a la derecha), en la misma escena y capa.
- Ctrl+Mayus+F10: solicitar la desaparicion de la instancia creada por Ctrl+Mayus+F9.
- Maximo: UN clon registrado por escena.
- Si la escena cambia, el clon anterior no se persigue entre escenas.
- No se copian ni sobrescriben estructuras de memoria completas del jugador;
  el modo usa las funciones propias de creacion de AGTK.

## Instalacion
1. Cierra el juego y guarda una copia de tus partidas.
2. Conserva el project.json ORIGINAL y player.exe ORIGINAL.
3. Quita la version.dll Stage13 anterior; no se pueden instalar dos proxies
   version.dll simultaneamente.
4. Extrae el ZIP descargado de la accion SUCCESS. Copia solo version.dll
   junto a player.exe. Si ya existia otro mod version.dll, no lo sobrescribas.
5. Entra a una escena de juego (NO al menu) y pulsa Ctrl+Mayus+F9 una vez.
6. Comprueba que aparece otro personaje. Pulsa Ctrl+Mayus+F10 para quitarlo.
7. Prueba el medidor Endurance: debe continuar en cero sin modificar HP/MP.
8. Cierra el juego y comparte EnduranceCloneStage23.log de la carpeta principal.

## Registro / diagnostico
- SOURCE_OK: EXE original SHA256 reconocido.
- HOOK_INSTALLED: tres puntos comprobados (setValue/addObject/removeObject).
- FREEZE2047_READY: permanece activo el cheat Endurance probado en Stage13.
- CLONE_MODE_READY: Ctrl+Mayus+F9/Ctrl+Mayus+F10 habilitados.
- PLAYER_CAPTURED: se localizo al actor principal en una escena y capa.
- CLONE_CREATED: el motor devolvio ID de instancia positivo.
- CLONE_SPAWN_REJECTED: el motor no pudo crear el clon.
- CLONE_DISAPPEAR_REQUESTED: Ctrl+Mayus+F10 pidio la desaparicion.
- CLONE_REMOVED_BY_ENGINE: el gestor del motor confirmo su retirada.
- CLONE_REFUSED / CLONE_MODE_DISABLED: una condicion de seguridad bloqueo la accion.
- FREEZE_2047_WRITE: Endurance sigue bloqueando la variable global 2047.

Si Ctrl+Mayus+F9 no hace nada, cambia de escena para que el motor registre de nuevo
el protagonista, o revisa PLAYER_CAPTURED en el log.

## Seguridad y limitaciones
- El juego posee un solo personaje controlable predeterminado.
  Crear otro objeto ID1 podria hacer que ambos respondan al teclado,
  afectar la camara, modificar eventos o interferir con partidas.
- La DLL no cambia player.exe ni project.json en disco, pero las acciones
  de spawn/desaparicion afectan la partida EN EJECUCION.
- No se ha comprobado en partida la creacion, la respuesta a las teclas,
  ni la eliminacion del duplicado; el CI solo comprueba simbolos/ABI,
  llamadas simuladas y exportaciones de Windows.
- Esta destinada exclusivamente a pruebas en una partida de respaldo.
- Si el juego crashea o aparece cualquier comportamiento anormal, cierra,
  retira version.dll y reinicia con el original.
- No uses Ctrl+Mayus+F9 durante una transicion o una escena cinematica.
- Si aparece CLONE_CREATED con object_captured=0, la retirada via Ctrl+Mayus+F10
  puede depender de la busqueda de instancia por el motor.
- Mantener Endurance=0 puede impedir secuencias que requieran 75/76 de tentacion.

## Codigo/validaciones
- Fuente integrada: experiments/clone_mode/endurance_clone_stage23.cpp
- Mock: experiments/clone_mode/test_clone_stage23.cpp
- Proyecto analizado: Forest of the Blue Skin Build29
- player.exe SHA256:
  02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea
- Endurance: only global AGTK ID2047 overridden in PlayVariableData::setValue;
  all other variable IDs, HP, MP, variables 2003/2386/2054, forwarded untouched.
- La funcion nativa ObjectAction::execActionObjectCreateForScript(int,int,int,int)
  genera nuevas instancias y devuelve su ID; Ctrl+Mayus+F9 la usa sobre objeto ID1.
- El motor administra la desaparicion mediante su funcion virtual
  Object::disappear(true) usada en los comandos nativos de escena.
