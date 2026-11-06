# Auditoría del juego de referencia: clon independiente (2026-11-06)

## Alcance y evidencias verificadas

- Origen: Release `fobs-reference-clone-input`, asset `project_decrypted.7z` (2.315.271 bytes).
- `project_decrypted.json`: 233.581.658 bytes, SHA-256 `d0e891051631b90478666b318fa11707e67485d5275d871fcacbf05dc0983e26`.
- `player.exe` referencia: 8.739.840 bytes, SHA-256 `847ccee0305f53f13a612501427c9bb179d95d37c06e6321404867e52dafad91`.
- `player.exe` Endurance canónico: 8.757.760 bytes, SHA-256 `02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea`.
- Auditoría estática, no ejecución del juego. GitHub Actions: JSON incremental con ijson, 7-Zip, pefile, comparación de símbolos y las pasadas headless con Rizin 0.9.1 y Ghidra 12.2. No se ejecutó ningún `player.exe`.
- 83 objetos, 15.239 acciones, 51 objetos con coincidencias heurísticas de nombres de duplicación (gran parte repetidos en eventos de enemigos). Los **51 son candidatos heurísticos**, no 51 clones únicos.

## Cadena comprobada desde project_decrypted.json

1. Jugador **objeto 1** (`プレイヤー`), acción **4** `分身発射` (lanzamiento de doble): comando de creación de **objeto 27**, acción **40**, `useConnect=true`, `connectId=5`.
2. Objeto **27** (`★味方が発射する弾`, categoría de proyectil aliado) contiene acciones del espejo. Su acción **48** `主人公発射` (lanzar al protagonista) ejecuta `objectCreate(objectId=19,actionId=22,useConnect=true,connectId=4,adjustY=-13)`.
3. Objeto **19** (`分身プレイヤー`, jugador doble), **93 acciones** propias: **22** inicio de doble, **25** desaparición, **33** cancelación con recuperación, **35** recuperación de HP, **77/78** desplazamiento lateral, **81** intercambio de posiciones, **83** movimiento de giro, **92** destrucción, **93** desactivación de manejo. El objeto 19 es **tipo distinto** del jugador ID1, no segunda instancia del ID1.
4. Objeto **72** `分身チェーン` (cadena del doble), **3 acciones**. Jugador ID1 acciones **328, 331 y 332** crean objeto72 como parte de la ruta de manejo.
5. Objeto **74** `分身プレイヤー(H後`, **91 acciones**: variante de doble posterior a eventos. Diversos enemigos (entre ellos ID51, ID69, ID92) tienen caminos explícitos `objectCreate` para objetos **19** y/o **74**.
6. Hay otros caminos de aparición directa de objeto19 desde el jugador (acciones **119** y **136**) y desde enemigos. No se debe afirmar que toda creación de doble pase siempre por el espejo27.

**Hallazgo especialmente importante:** la existencia de un tipo propio permite programar condiciones y destinatarios específicos para el doble. Los scripts de los enemigos incluyen acciones diferenciadas para ese tipo, a diferencia de Stage49, donde original y clon están ambos en la lista de ID1.

**Advertencia sobre aislamiento:** algunas acciones del objeto19 escriben deliberadamente variables del jugador ID1 con cualificador `-2`. Por ejemplo, acción **22** escribe `2045=-1`, acción **25** escribe `2045=0`, y acción **35** utiliza un cambio de `variableId=2` con `variableObjectId=1`, `variableQualifierId=-2` y valor `20` (acción nombrada `HPの回復`). La independencia del tipo de objeto **no demuestra aislamiento absoluto de todas las variables/eventos**. No copiar esas escrituras a Endurance sin analizar su intención.

## Comparación de funciones exportadas del motor

Ambos binarios PE32 tienen **8.192 exportaciones**, de las cuales **8.187** coinciden en nombre. La similitud de motor **no implica compatibilidad binaria de hooks ni de ABIs**.

| Función nativa (nombre abreviado) | Endurance RVA | Referencia RVA | Observación |
|---|---:|---:|---|
| `ObjectAction::getTargetObjectById` | 0x14D320 | 0x14D080 | Misma cabecera, diferencias internas |
| `ObjectAction::getTargetObjectByGroup` | 0x14D270 | 0x14CFD0 | 32 bytes iniciales idénticos |
| `ObjectAction::getTargetObjectInstanceId` | 0x14D420 | 0x14D180 | 32 bytes iniciales idénticos |
| `GameManager::getTargetObjectByInstanceId` | 0x1E8470 | 0x1E77A0 | Cabecera similar, diferencias |
| `GameManager::getTargetObjectListByObjectId` | 0x1E8500 | 0x1E7830 | Cabecera similar, diferencias |
| `Scene::getObjectPlayer` | 0x197780 | 0x1973D0 | 32 bytes iniciales idénticos |
| `SceneLayer::addObject` | 0x18B380 | 0x18B0D0 | 32 bytes iniciales idénticos |
| `PlayObjectData::addHp` | 0x6C670 | 0x6C5E0 | 32 bytes iniciales idénticos |
| `Object::checkAttackableObject` | 0x12FFC0 | 0x12FD30 | 32 bytes iniciales idénticos |
| `ObjectAction::execActionObjectCreate` | 0x13FC20 | 0x13F990 | Diferencias |
| `ObjectAction::checkLinkConditionObjectHit` | 0x154920 | 0x154680 | Diferencias |
| `Object::damaged` | 0x12F760 | 0x12F4F0 | **Firma C++ exportada diferente** |

**Cambio de ABI relevante:** la exportación de Endurance es `?damaged@Object@agtk@@QAEXPAV12@PAVPlayObjectData@data@2@0@Z`, mientras que la referencia utiliza `?damaged@Object@agtk@@QAEXPAV12@PAVPlayObjectData@data@2@@Z`. El sufijo adicional del nombre decorado indica una lista distinta de tipos de parámetros: no es correcto trasplantar el hook de daño ni su firma de llamada sin adaptar y verificar.

## Implicación para Stage64 (sin modificar el núcleo)

- **No** trasladar literalmente RVAs o bytes entre los ejecutables.
- **No** basta con cambiar la identidad del objeto Stage49: el proyecto Endurance usa otras definiciones de objetos y enemigos; hay que establecer una entidad del clon que el motor pueda instanciar con datos/acciones/colliders válidos.
- Investigar la implementación de un **tipo de objeto independiente**, con acción/vida/daño propios y comportamiento autónomo; un emisor separado es opcional (el otro juego tiene varios caminos de creación).
- Para aislar los eventos, analizar/reproducir **las ramas específicas de objetivo por enemigo** y no reenviar globalmente el ID1. Mantener UI, menús, Endurance y original sin redirecciones indiscriminadas.
- Evitar copiar las escrituras del objeto19 que modifican intencionadamente las variables del jugador.
- Queda pendiente demostrar aislamiento de daño/eventos mediante ejecución y trazas del juego de referencia. Estas conclusiones son **estáticas**.

## Ejecuciones verificadas

- Rizin + Ghidra + auditoría incremental: https://github.com/Chaborsz/Temporary/actions/runs/42272165481
- Comparación RVA/firma y análisis dirigido de acciones: https://github.com/Chaborsz/Temporary/actions/runs/42273682153

No se ha modificado Stage49, Stage53 ni Stage64, ni ninguna de sus DLL funcionales.
