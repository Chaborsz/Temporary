# STAGE 65 — Clon de tipo independiente: auditoría de viabilidad y matriz de rutas

**Estado:** `STAGE65_STATIC_AUDIT=PASS` · `TYPED_CLONE_RUNTIME_READY=NO` · `VERSION_DLL_MODIFIED=NO` · `DIAGNOSTICS_DLL_MODIFIED=NO`

## Fuente y reproducibilidad

La auditoría se ejecutó directamente en `Chaborsz/Temporary` sobre el juego original Endurance, no sobre el juego de referencia:

- `fobs-build29-endurance-input/project_data.zip`, verificado y extraído con **7-Zip**.
- `project_decrypted.json`: **301.997.021 bytes**, SHA-256 `2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89`.
- `cheats/endurance/input/player.exe`: **8.757.760 bytes**, SHA-256 `02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea`.
- [Auditoría Stage65 con inventario de rutas](https://github.com/Chaborsz/Temporary/actions/runs/42275577389), job PASS.
- [Artefacto descargable de la matriz](https://github.com/Chaborsz/Temporary/actions/runs/42275577389/artifacts/13533685066).

## Hechos comprobados en Endurance

- **206** tipos de objeto, **24.030** acciones, **89.742** comandos.
- Jugador = tipo **1**, **462** acciones, **1.917** comandos, **1.213** enlaces.
- **146 tipos de objeto distintos del jugador** incluyen campos que hacen referencia explícita a `objectId=1` u otros parámetros del jugador.
- **16.513** referencias al ID1 en todas las clases, de las cuales **15.626** son externas a la clase del jugador. Una referencia **no implica necesariamente un ataque o evento ejecutado**.

### Clasificación exhaustiva de las 16.513 referencias

| Tipo | Número |
| --- | ---: |
| Variables o switches con alcance explícito al jugador ID1 | **14.278** |
| Selección/creación de objeto, ejecución de acción y movimiento | **1.563** |
| Lecturas de variables como origen de asignación | **672** |

Detalles de campos:
- `switchVariableChange.variableObjectId=1`: **7.831**.
- `switchVariableChange.switchObjectId=1`: **6.447**.
- `objectMove.targetObjectId=1`: **762**.
- `actionExec.objectId=1`: **749**.
- `switchVariableChange.assignVariableObjectId=1`: **672**.
- `objectLock.objectId=1`: **50**.
- `objectCreate.objectId=1`: **2**.

Estas categorías cumplen funciones **diferentes**. Un redireccionamiento global al clon de todo `ID1` alteraría el HUD, las acciones del jugador, la UI, los controles y el desarrollo normal del juego.

### Ámbito de los cuatro efectos críticos en los datos del proyecto

| Variable | Referencias a comandos | `variableObjectId` | `variableQualifierId` | Interpretación |
| --- | ---: | ---: | ---: | --- |
| `2044` | **2.739** | `1` | `-2` | Dirigida a la clase del jugador |
| `2031` | **785** | `1` | `-2` | Dirigida a la clase del jugador |
| `2047` | **2.447** | `0` | `-1` | Global; sigue congelada por Endurance |
| `2003` | **1.992** | `0` | `-1` | Global; no se puede asignar naturalmente a una instancia |

Son referencias a comandos del proyecto; no equivalen a número de ejecuciones en una sesión. **Corrige la simplificación anterior:** las escrituras `2044` y `2031` no son globals en la definición del proyecto, mientras que `2003` y `2047` sí utilizan alcance global.

## Comparación con el juego de referencia

El juego de referencia contiene objetos de tipo:
- ID1 jugador;
- ID27 proyectil/espejo, que desde su acción 48 crea `objectId=19, actionId=22`;
- ID19 jugador-doble (93 acciones independientes);
- ID74 variante posterior a eventos y ID72 cadena.

En **Endurance** los ID **19** y **74** están ocupados por clases de objeto no equivalentes; el **27** no figura en las definiciones. Aunque 27 sea una laguna numérica, **tener un ID libre no crea un tipo de objeto válido** ni añade sus datos de animación, colisión, reglas y acciones.

El motor de los dos títulos comparte 8.187 exportaciones por nombre, pero no exactamente sus direcciones ni todas sus firmas; `Object::damaged` **cambia de firma**, por lo que no se deben copiar hooks binarios.

## Decisión técnica y criterios de implementación

**No sustituir Stage53/Stage49 en este punto**: su clon ID1 existe y F9/F10 y Endurance funcionan. Convertirlo simplemente en un tipo inexistente o en una clase ajena puede provocar errores o producir un actor que los enemigos ignoren.

Hay dos líneas de trabajo válidas, que no deben confundirse:

1. **Clon de tipo realmente independiente**. Exige registrar datos de objeto completos con nuevo ID propio, animaciones/colisión/estados y rutas de evento que reconozcan ese tipo. Requiere un punto de carga/registro verificable o parcheo de datos del proyecto con sustitución segura; **no hay prueba todavía de ese mecanismo en Endurance**.
2. **Aislamiento por instancia conservando ID1**. Utiliza las dos instancias y sus datos físicos ya existentes; intercepta **solo** los efectos correspondientes a una víctima comprobada mediante una condición de colisión/impacto de esa acción, sin reescribir todos los IDs. Requiere atribución de emisor, víctima y contexto, sobre todo para `2044`/`2031` jugador y `2003` global. **No aplicar reglas de distancia o supresión global sin atribución causal.**

**Orden preferente**: preservar la instalación modular existente, trabajar el aislamiento por instancia con evidencia de Stage63/64 y reservar un nuevo tipo de objeto para cuando esté probado el registro de definiciones y su cobertura por los enemigos. El segundo juego da el diseño, no un parche que pueda copiarse.

## Próximo bloque de implementación (no ejecutado aún)

- Identificar y verificar funciones de selección/registro de `ObjectData` y la atribución de `ObjectAction` a la víctima real.
- Separar rutas `actionExec`/`objectMove` (1.511 referencias), variables/switches y lectura de RHS, con políticas independientes.
- Instrumentar/implementar en módulo desmontable, **sin crear dependencia obligatoria de diagnósticos**.
- Guardar inmutable `version.dll` Stage53 y el congelamiento de Endurance, y validar contra acciones de distintos enemigos antes de adoptar una build funcional.

## Archivos adjuntos al artefacto

- `STAGE65_CLASS_FEASIBILITY.json`: objetos, clases, spawns, rutas, muestras y exportaciones nativas.
- `STAGE65_ROUTE_MATRIX_SUMMARY.json`: matriz cuantificada y ámbitos reales.
- `STAGE65_PLAYER_ID1_REFERENCES.csv`: cada referencia del proyecto a ID1, con acción, comando, parámetro y alcance.
- `STAGE65_CRITICAL_VARIABLE_COMMANDS.csv`: cada comando de `2003/2031/2044/2047`, con ámbito y operador.
- `STAGE65_FEASIBILITY_ES.md`: resumen de CI.
- `original_object_inventory.csv` e hashes de entrada.

**No confundir** el PASS de auditoría estática con una modificación/ejecución de DLL dentro del juego. `TYPED_CLONE_RUNTIME_READY=NO`.
