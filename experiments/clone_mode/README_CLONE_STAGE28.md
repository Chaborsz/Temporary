# Stage28 — corrección del rechazo de clones

El registro real de Stage27 confirma que el objeto clon se crea y es eliminado por una comprobación falsa:
`CLONE_CONTROLLER_REFUSED: original player has no active controller.`

Stage28 NO rechaza el controlador original por ser -1. Solo exige que los objetos
y sus PlayObjectData sean distintos, que el controlador original permanezca
inalterado y que el setter nativo pueda dejar el clon con controlador -1.

Si el clon YA tenía controlador -1, se emite `CLONE_CONTROLLER_NOOP_WARNING`;
**esto no demuestra independencia**. Se deja la instancia para poder observar
si conserva el movimiento vinculado. Si sigue vinculado, habrá que identificar
el origen real del movimiento sin modificar el objeto original.

Atajos: **F9** alterna crear/quitar; **F10** elimina. F6 reinicia como siempre.

Registro: `EnduranceCloneStage28.log` junto a `player.exe`.
Busca `CLONE_CONTROLLER_STATE`, `CLONE_CREATED` y, si aplica,
`CLONE_CONTROLLER_NOOP_WARNING`. Entrega esas líneas y observa si el clon
se mueve al desplazarse el protagonista.

Instalación: cerrar juego, respaldar partidas, sustituir solo `version.dll`
de Stage27 por la de Stage28 junto a player.exe. Conservar `project.json`
original. Nunca sobrescribir una `version.dll` de otro mod.
Para revertir, cerrar juego, quitar esta DLL y restaurar Stage13 o Stage27.
Es una build experimental sin prueba de jugabilidad real.
El filtro Endurance de global 2047 se conserva.

---
## Independencia del clon respecto al jugador original

La versión anterior generaba otro objeto jugable ID1 que heredaba el mando del original.
Stage28 mantiene una segunda instancia real para los eventos, pero llama a la
rutina nativa PlayObjectData::setControllerId(-1) sobre los datos particulares
del CLON, nunca sobre los del jugador.

Comprobaciones antes de mantener el clon:
- Los objetos original y clon son distintos y sus PlayObjectData no se comparten.
- El jugador original conserva su identificador de controlador.
- El motor informa controlador -1 para la instancia clonada.
- Si una comprobación falla, se solicita desaparecer la instancia recién creada.

No desactiva colisiones ni convierte al clon en un objeto puramente decorativo.
Sí podría haber lógica compartida del propio objeto ID1 a nivel de escenas y
variables globales; la independencia total de eventos sigue pendiente de juego real.

## Nuevas teclas

- F9: alterna crear o retirar el clon (una pulsación).
- F10: retirar el clon (segundo atajo de seguridad).
- NO se requieren Ctrl ni Mayús.
- F6 permanece reservado para el reinicio original.

La auditoría de inputMapping del project.json no encontró F9/F10 asignadas.
Eso no certifica los atajos internos del motor ni otras capas del sistema.

## Registro esperado

- CLONE_MODE_READY F9=toggle clone F10=remove
- CLONE_CONTROLLER_STATE original=X->X clone=Y->-1
- CLONE_INPUT_INDEPENDENT: original retains controller
- CLONE_CREATED: objeto original ID1, instancia nueva, misma escena y capa
- CLONE_ISOLATION_FAILED: se rechazó la independencia y se solicitó eliminar

Si el duplicado sigue moviéndose con el protagonista pese a 
CLONE_INPUT_INDEPENDENT, la vinculación procede de otra ruta de control;
no se debe ocultar ni forzar su posición sin analizarla.


---

# Endurance + Clone Mode Stage28 — prueba experimental x86

**Estado:** build experimental; NO se ha ejecutado en una partida real.
Conserva el cheat Endurance Stage13 que el usuario confirmo funcional.

## Controles
- F9: crear/retirar una segunda instancia del objeto jugable ID1 (プレイヤー) al lado
  del jugador actual (56 px a la derecha), en la misma escena y capa.
- F10: solicitar la desaparicion de la instancia creada por F9.
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
5. Entra a una escena de juego (NO al menu) y pulsa F9 una vez.
6. Comprueba que aparece otro personaje. Pulsa F10 para quitarlo.
7. Prueba el medidor Endurance: debe continuar en cero sin modificar HP/MP.
8. Cierra el juego y comparte EnduranceCloneStage28.log de la carpeta principal.

## Registro / diagnostico
- SOURCE_OK: EXE original SHA256 reconocido.
- HOOK_INSTALLED: tres puntos comprobados (setValue/addObject/removeObject).
- FREEZE2047_READY: permanece activo el cheat Endurance probado en Stage13.
- CLONE_MODE_READY: F9/F10 habilitados.
- PLAYER_CAPTURED: se localizo al actor principal en una escena y capa.
- CLONE_CREATED: el motor devolvio ID de instancia positivo.
- CLONE_SPAWN_REJECTED: el motor no pudo crear el clon.
- CLONE_DISAPPEAR_REQUESTED: F10 pidio la desaparicion.
- CLONE_REMOVED_BY_ENGINE: el gestor del motor confirmo su retirada.
- CLONE_REFUSED / CLONE_MODE_DISABLED: una condicion de seguridad bloqueo la accion.
- FREEZE_2047_WRITE: Endurance sigue bloqueando la variable global 2047.

Si F9 no hace nada, cambia de escena para que el motor registre de nuevo
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
- No uses F9 durante una transicion o una escena cinematica.
- Si aparece CLONE_CREATED con object_captured=0, la retirada via F10
  puede depender de la busqueda de instancia por el motor.
- Mantener Endurance=0 puede impedir secuencias que requieran 75/76 de tentacion.

## Codigo/validaciones
- Fuente integrada: experiments/clone_mode/endurance_clone_stage28.cpp
- Mock: experiments/clone_mode/test_clone_stage28.cpp
- Proyecto analizado: Forest of the Blue Skin Build29
- player.exe SHA256:
  02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea
- Endurance: only global AGTK ID2047 overridden in PlayVariableData::setValue;
  all other variable IDs, HP, MP, variables 2003/2386/2054, forwarded untouched.
- La funcion nativa ObjectAction::execActionObjectCreateForScript(int,int,int,int)
  genera nuevas instancias y devuelve su ID; F9 la usa sobre objeto ID1.
- El motor administra la desaparicion mediante su funcion virtual
  Object::disappear(true) usada en los comandos nativos de escena.
