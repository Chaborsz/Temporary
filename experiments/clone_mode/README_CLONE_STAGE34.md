# Stage34 — Recuperación del protagonista después de cambiar de escena

El usuario validó la ejecución del filtro `ObjectMovement::move` sobre el clon y el
funcionamiento de crear/quitar instancias. Su registro también mostró que, después
de `PLAYER_REMOVED_BY_ENGINE`, F9 dejó de crear clones por falta de jugador capturado.

**Corrección Stage34:** F9 resuelve el protagonista de la escena activa mediante
`Scene::getObjectPlayer()` (VA `0x00597780`) cuando la referencia anterior falta
o pertenece a otra escena. Verifica ID1 y que la capa pertenezca a esa escena.
Rechaza la referencia del clon previamente registrado. Nunca reutiliza el puntero
del personaje destruido ni escanea memoria arbitraria. La desaparición del jugador
solo invalida los punteros al actor y conserva el identificador del hilo de juego.

**Controles:** F9 crear/retirar, F10 retirar; F6 es el reinicio original.
**Registro:** `EnduranceCloneStage34.log`.
Busca `PLAYER_REMOVED_BY_ENGINE: actor references cleared; game thread retained.`
y después `PLAYER_REACQUIRED_FROM_SCENE object_id=1` cuando pulses F9 en otra escena.

Se mantienen sin cambios la supresión del movimiento del clon, la creación/eliminación
con funciones nativas y el freeze Endurance del global ID2047.

**Límite:** cuando `Scene::getObjectPlayer()` todavía no encuentre un protagonista
al cargar una escena, el clon se rechaza de forma segura y puede intentarse otra
vez después de que termine de cargar. No se promete recuperar jugadores de
cinemáticas o escenas sin protagonista real.

**Prueba:** cierra el juego y sustituye la version.dll anterior por la Stage34.
Usa partida de respaldo, crea un clon, retíralo, atraviesa una transición de escena
y vuelve a pulsar F9. Comprueba si reaparece y si el filtro de movimiento se aplica.
Envía `EnduranceCloneStage34.log` para comprobar la re-adquisición.

---
# Clone Stage34 — movimiento separado por instancia (experimental)

## Evidencia de la partida
- Stage28 sí crea y retira correctamente las instancias clonadas: CLONE_CREATED, CLONE_DISAPPEAR_REQUESTED, CLONE_REMOVED_BY_ENGINE.
- El controlador -1 ya era el mismo en ambos: `original=-1->-1 clone=-1->-1`; el setter no neutraliza movimiento.
- El clon sigue moviéndose vinculado con el protagonista. El motor puede aplicar entrada a ambos objetos ID1.
- Tras PLAYER_REMOVED_BY_ENGINE no hay referencia a jugador capturado; Stage34 conserva la protección contra usar punteros ya retirados.

## Solución técnica Stage34
- Se conserva el `version.dll` proxy (Windows x86) y el freeze Endurance del global ID2047.
- En lugar de modificar controlador -1, se intercepta exclusivamente `ObjectMovement::move(float)` RVA 0x11A020.
- Estructura nativa: `ObjectMovement + 0x18` es puntero al Object propietario.
- La función recibe `Vec2*` de retorno oculto por ABI MSVC x86 y `float` de delta de tiempo.
- Si y solo si propietario == clon registrado y hay instancia activa, se devuelve desplazamiento (0,0).
- Si el objeto es el protagonista u otro, se llama al método original sin modificar los parámetros.
- No se anula actualización del objeto, sistema de eventos, registro de colisiones o acciones, aunque neutralizar `move` puede afectar también gravedad/desplazamientos programados del clon; por ello es experimental.
- Al retirar al clon, el filtro deja de aplicarse.
- En F9 se intenta crear o retirar un clon; F10 retira. F6 conserva el reinicio nativo.
- El controlador no se toca; los datos de juego del original y el clon deben ser distintos.

## Instalación y prueba
1. Cierra el juego. Usa una partida de respaldo.
2. Mantén `player.exe` y `Resources/data/project.json` originales.
3. Quita `version.dll` Stage28 y coloca la `version.dll` Stage34 junto a player.exe. No sobreescribas otra DLL preexistente de terceros.
4. En una escena jugable, pulsa F9 para crear un clon. Camina unos pasos: el clon debería permanecer inmóvil en el punto donde apareció.
5. Comprueba que Endurance continúa congelado y que el clon participa en los disparadores de eventos necesarios.
6. Pulsa F9 o F10 para retirarlo. Comprueba que el clon desaparece.
7. Cierra el juego y comparte `EnduranceCloneStage34.log` junto a tus observaciones.

## Mensajes del registro
- `CLONE_MODE_READY`: F9/F10 y los cuatro hooks instalados.
- `PLAYER_CAPTURED`: instancia original localizada.
- `CLONE_IDENTITIES_SEPARATE`: datos independientes, sin tocar mandos.
- `CLONE_CREATED`: nueva instancia creada por el motor.
- `CLONE_MOVEMENT_BLOCKED`: la nueva ruta de bloqueo fue realmente ejecutada en el juego.
- `CLONE_MOVEMENT_GATE_READY`: ruta preparada, **no** implica llamadas reales.
- `CLONE_REMOVED_BY_ENGINE`: se retiró la instancia.
- `FREEZE_2047_WRITE`: la función Endurance permanece activa.

## Límites
- **No se ha probado en una partida real**. Los tests nativos verifican la ABI, el filtrado y la compilación, pero no movimiento/jugabilidad.
- Si no aparece `CLONE_MOVEMENT_BLOCKED` y el clon sigue moviéndose, el movimiento vinculado usa otra ruta del motor.
- Si aparece `CLONE_MOVEMENT_BLOCKED` pero el clon todavía se mueve, hay otro movimiento que no pasa por esta función.
- `ObjectMovement::move` también interviene en física/acciones: no se garantiza que el clon pueda moverse por scripts, gravedad o ser empujado.
- Si algo falla, cierra el juego, elimina esta `version.dll` y vuelve a la DLL Stage13 comprobada (Endurance).

## Fuente
- `experiments/clone_mode/endurance_clone_stage34.cpp`
- `experiments/clone_mode/test_clone_stage34.cpp`
- `.github/workflows/clone-stage34-dll.yml`