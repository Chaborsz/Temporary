# Stage 41 — Diagnóstico del destinatario de eventos del clon

## Evidencia confirmada
- Stage38: TARGET_RESOLVE kind=2 request=313 result=original caller_rva=0x1E7074.
- Stage39 demostró que el llamador es GameManager::getVariableValue: está leyendo una variable del objeto original, NO seleccionando al destinatario del ataque.
- El clon sí activa eventos, pero los efectos posteriores siguen aplicándose al protagonista original.
- Las DLL previas mantienen la creación/eliminación F9/F10, recuperación tras transiciones, bloqueo del movimiento del clon y Endurance.

## Qué observa Stage41 (sin redirigir ningún objetivo)
- GameManager::getTargetObjectListByObjectId(id) (RVA 0x1E8500): registra ID solicitado, número de objetos y presencia del original/clon.
- Object::damaged(attacker, data1, data2) (RVA 0x12F760): registra víctima y atacante si alguno es original o clon.
- PlayObjectData::addHp(delta) (RVA 0x6C670): registra cambios de HP recibidos por las instancias original y clon.
- Conserva las tres consultas de Stage38: getObjectPlayer, getObjectInstance y getTargetObjectByInstanceId.
- Los valores retornados por cada función y los argumentos originales se conservan exactamente; no se cambia ningún destino ni se fabrican daños.
- El archivo generado es EnduranceCloneStage41.log junto a player.exe.

## Cómo probar
1. Cierra el juego. Mantén copia de seguridad de partidas y Resources/data/project.json original.
2. Reemplaza ÚNICAMENTE version.dll Stage38 por la incluida en el ZIP Stage41, al lado de player.exe.
3. Entra en una escena jugable y pulsa F9 para crear el clon.
4. Deja un breve periodo sin contacto; luego haz que el clon active un evento que normalmente provoca un ataque sobre el protagonista.
5. Sin cerrar la escena inmediatamente, comprueba visualmente a quién afecta. Retira el clon con F10, cierra el juego y comparte EnduranceCloneStage41.log.
6. Las líneas relevantes serán TARGET_LIST, DAMAGE_CALL y HP_CHANGE, además de TARGET_RESOLVE.

## Interpretación
- TARGET_LIST id=1 original=1 clone=1: el motor recibió ambos objetos como posibles destinos en la misma lista; aún no implica que una acción haya elegido a uno.
- DAMAGE_CALL victim=original y attacker=other/clone: ataque ejecutado sobre el original; debe analizarse el camino exacto de ataque.
- HP_CHANGE target=original: modificación directa del HP original. Si no hay DAMAGE_CALL puede ser script o cálculo directo.
- Si no aparece DAMAGE_CALL/HP_CHANGE durante el evento, sus consecuencias usan rutas diferentes (acción, animación, estado o scripts de escena) y habrá que analizarlas.
- Esta versión NO corrige aún a quién afectan los eventos. No se debe redirigir indiscriminadamente GameManager::getVariableValue.

## Controles y seguridad
- F9: crear o retirar; F10: retirar; F6 conserva su reinicio nativo.
- Endurance global 2047 sigue bloqueado a cero; HP/MP y otros valores solo se observan.
- Las comprobaciones protegen el exe canónico por tamaño/SHA256 y prueban prólogos antes de instalar hooks.
- Esta versión es experimental, compilada con pruebas Windows x86, pero sin validación de juego real.
- Si hay un fallo, cierra el juego y restaura la Stage34 o la Stage13 conocida.

## Fuentes
- experiments/clone_mode/endurance_clone_stage41.cpp
- experiments/clone_mode/test_clone_stage41.cpp
- .github/workflows/clone-stage41-dll.yml