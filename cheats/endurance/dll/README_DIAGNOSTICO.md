# Endurance — DLL de diagnóstico sin modificación del juego

**Objetivo:** comprobar si el medidor del corazón situado debajo de LIFE y MP utiliza la variable global 2047, 2003, 2386 o 2054, o si estas se modifican fuera de GameManager::assignVariableData.

## Instalación

1. Cierra el juego. Si tienes la DLL anterior, retira **version.dll** de la carpeta de **player.exe**. No la conserves en paralelo.
2. Comprueba que tu **project.json** es el original, sin los cambios Stage9.
3. Descarga el artefacto que terminó en SUCCESS de **Endurance 2047 diagnostic x86**.
4. Extrae y copia solo **version.dll** a la carpeta de **player.exe**. NO va dentro de Resources/data ni System32.
5. Inicia el juego; usa una partida de prueba y provoca un cambio visible en la barra del corazón mientras juegas durante al menos 10 segundos.
6. Cierra el juego. Copia aquí el contenido de **EnduranceDiagnostic.log**.

## Interpretación

- SOURCE_OK: ejecutable correcto.
- HOOK_INSTALLED: la función fue instrumentada (no implica que reciba llamadas).
- FIRST_CALL: primeros ejemplos de variables y operador, **sin alterar ningún valor**.
- COUNTERS: sumas de asignaciones interceptadas:
  - total: llamadas observadas al punto instrumentado.
  - id2047: todas las asignaciones a 2047.
  - global2047: 2047 sin objeto asociado.
  - object2047: 2047 asociado a algún objeto.
  - id2003: medidor de eyaculación.
  - id2386: variable visual derivada del medidor.
  - id2054: estado de excitación 0/1.
  - other: todas las demás variables.
- Si total=0 después de provocar el cambio del HUD, **esta ruta no está observando las escrituras** y habrá que examinar GameManager::assignVariableData o interceptar otra ruta.
- Si id2047=0 pero id2003>0 durante el cambio visual, el medidor podría ser 2003; **no se afirma identidad sin correlación temporal**.
- Si global2047=0 pero object2047>0, el filtro de la DLL anterior habría ignorado esas escrituras.

## Seguridad / límites

- No modifica variables, archivos del juego, HP, MP, guardados, ni el valor de Endurance.
- Proxy VERSION.dll x86 con el mismo guard de SHA256 de player.exe y el mismo hook previamente compilado.
- El hook puede generar un coste mínimo; registra solo los primeros dos eventos por categoría y un contador cuando cambia el total.
- El análisis no incluye telemetría externa ni descarga recursos.
- Si otra versión.dll ya existe, **no la sobrescribas** sin respaldarla.
- Para quitarla, cierra el juego y borra la version.dll añadida.

Estado: los tests CI comprueban la lógica, pero no sustituyen la prueba dentro del juego.
