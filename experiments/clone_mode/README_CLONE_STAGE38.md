# Stage 38 — Diagnóstico del objetivo de eventos (solo lectura)

## Problema confirmado
Stage34 crea y retira clones ID1 y el filtro de movimiento del clon se ejecuta.
El usuario confirmó que la colisión del clon detona los eventos, pero las acciones
posteriores atacan al protagonista original. Esta es una cuestión de selección
del destinatario del evento, NO de generación ni de movimiento.

## Qué añade esta versión
Conserva íntegro el filtro Endurance global ID2047 y el movimiento individual.
Agrega tres interceptores de lectura que **devuelven exactamente los mismos
objetos que el motor devolvería sin la DLL**:
- Scene::getObjectPlayer() — RVA 0x197780.
- Scene::getObjectInstance(objectId,instanceId,scope) — RVA 0x19BE80.
- GameManager::getTargetObjectByInstanceId(instanceId) — RVA 0x1E8470.

Solo cuando hay un clon activo, registra los lugares del ejecutable que consultan
el jugador o las instancias y si la búsqueda devuelve ORIGINAL, CLONE, OTHER o NULL.
Las líneas usan la forma:
`TARGET_RESOLVE kind=0 request=0 result=original caller_rva=0x... site_calls=1`
`kind=0` significa getObjectPlayer, `kind=1` getObjectInstance(ID1),
`kind=2` getTargetObjectByInstanceId.
Los registros se limitan a los primeros accesos y a hitos por llamador para
no escribir un archivo por cada fotograma. No se interceptan ataques ni daño.

## Instalación y ensayo
1. Cierra el juego; utiliza una partida de respaldo.
2. Deja player.exe y project.json originales. Sustituye solamente la version.dll
   Stage34 por la version.dll de este artefacto junto al ejecutable.
3. En una escena sin evento, pulsa F9 y observa el clon unos segundos.
4. Haz que el clon active un evento que normalmente termine atacando al
   protagonista. Juega hasta observar el efecto.
5. Pulsa F10 para retirar el clon y cierra el juego.
6. Comparte **EnduranceCloneStage38.log** e indica aproximadamente qué ocurrió
   entre la creación y el ataque. Se pueden comparar los caller_rva de ambas fases.

## Controles
- F9 crear/retirar un clon; F10 retirar; F6 mantiene reinicio original.

## Interpretación importante
- Un `TARGET_RESOLVE` devolviendo `original` durante el evento es un candidato
  a analizar, no prueba por sí solo de que ese llamador produzca el ataque.
- Si las tres rutas no muestran el evento, el script puede usar referencias
  directas u otras rutas de selección de acciones; no se autoriza redirección global.
- Esta es una DLL diagnóstica EXPERIMENTAL; no corrige todavía el objetivo del evento.
- No modifica player.exe ni project.json. Si algo falla, restaura Stage34 o Stage13.

## Fuentes
- experiments/clone_mode/endurance_clone_stage38.cpp
- experiments/clone_mode/test_clone_stage38.cpp