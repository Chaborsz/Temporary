# Forest of the Blue Skin — Stage43: diagnóstico de acciones de eventos

## Hallazgo previo confirmado
- Stage41 registró `TARGET_LIST id=1 count=2 original=1 clone=1`.
- `caller_rva=0x1E604E` pertenece a `GameManager::getSwitchVariableDataList`: lista para acceso a interruptores/variables, no prueba de selección de ataque.
- `caller_rva=0x1E7074` pertenece a `GameManager::getVariableValue`: lectura de variable por instancia, tampoco ataque.
- No hubo `DAMAGE_CALL` ni `HP_CHANGE` en el evento observado; esto apunta a comandos/acciones/scripts, no daño/HP nativos (sin demostrar aún ruta exacta).

## Funciones nuevas en Stage43
- `ObjectAction::getTargetObjectInstanceId` (RVA 0x14D420) — registra la instancia elegida por una acción.
- `ObjectAction::execActionActionExec` (RVA 0x148530) — ejecución de otra acción.
- `ObjectAction::execActionScriptEvaluate` (RVA 0x149980) — scripts en la acción.
- `ObjectAction::execActionSwitchVariableChange` (RVA 0x146470) — cambios de interruptores y variables.
- `ObjectAction::execActionObjectChange` (RVA 0x1401A0) — cambios del objeto en la escena.
- Estas cinco rutas son diagnósticas; devuelven y pasan exactamente los resultados/argumentos originales. No redirigen ningún ataque.
- `ObjectAction+0x50` contiene el objeto ejecutor; los registros diferencian su ID, instancia y si es original o clon.
- El registro limita entradas por punto de llamada y objeto ejecutor para acotar la escritura.

## Qué se conserva
- Endurance global ID2047 bloqueado a cero.
- Clon auténtico del objeto ID1, creación con F9 y retirada con F9/F10.
- Neutralización de ObjectMovement únicamente para el clon.
- Recuperación del protagonista tras transiciones de escena.
- Resolución general de instancia y sus lecturas de Stage38 y Stage41 sin cambios.

## Prueba
1. Cierra el juego, respalda una partida y conserva `player.exe` y `project.json` originales.
2. Reemplaza la versión anterior de `version.dll` por Stage43, junto a `player.exe`.
3. Entra en una escena jugable, pulsa F9 y deja al clon unos segundos sin provocar evento.
4. Provoca un evento con el clon que habitualmente afecta al original. Comprueba visualmente el resultado.
5. Retira con F10, cierra el juego y comparte `EnduranceCloneStage43.log`.
6. Busca `EVENT_ACTION`, especialmente `kind=0` (`getTargetObjectInstanceId`) con `target=original` y `owner_id` del activador.

## Claves del registro
- `EVENT_ACTION kind=0`: resolución concreta de un objeto, se observan `args` y `target=original|clone|other|null`.
- `EVENT_ACTION kind=1`: execActionActionExec.
- `EVENT_ACTION kind=2`: execActionScriptEvaluate.
- `EVENT_ACTION kind=3`: execActionSwitchVariableChange.
- `EVENT_ACTION kind=4`: execActionObjectChange.
- `EVENT_ACTION_TRACE_READY`: interceptores instalados; no significa que se ejecutaran durante el evento.
- `DAMAGE_CALL`/`HP_CHANGE` siguen disponibles para confirmar daño convencional.

## Precauciones
- Nueva DLL experimental, no confirmada en partida real. Hay cinco hooks adicionales, por lo que es recomendable una partida de prueba.
- Si se produce un fallo, cierra el juego y restaura la DLL Stage34 o Stage13.
- Los registros de acciones pueden tener mucho volumen; usan muestreo por llamador y evento.
- Evita interpretar un `target=original` aislado como prueba de la acción causante: hay que correlacionarlo con el evento.
- No modifica los archivos del juego en disco.