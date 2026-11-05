# Endurance Stage12 - Writer-Path Diagnostic DLL (x86)

**Tipo:** prueba de diagnostico de lectura. NO modifica Endurance, HP, MP ni los archivos del juego.

El hook anterior mostro COUNTERS total=0 en partida.
Esta version utiliza **PlayVariableData::setValue (RVA 0x6AB90)** y
**PlayVariableData::requestValue (RVA 0x6ACB0)**, identificados en el
player.exe original. Cuenta asignaciones para los IDs 2047, 2003, 2386, 2054 y otros.

## Instalacion y prueba

1. Cierra el juego y conserva el project.json original. Haz copia de las partidas.
2. Retira el version.dll de la prueba anterior. Si ya habia otro version.dll
   antes de instalar nuestros mods, no lo sobrescribas.
3. Descarga un artefacto de ejecucion SUCCESS del workflow:
   https://github.com/Chaborsz/Temporary/actions/workflows/endurance-stage12-writers-dll.yml
4. Copia exclusivamente version.dll junto a player.exe, nunca en Resources/data.
5. Entra al juego y deja la barra del corazon en reposo. Despues provoca un cambio
   visible de la barra durante al menos 10 segundos.
6. Cierra el juego y comparte el archivo EnduranceWriters.log de la carpeta principal.

## Interpretacion

- SOURCE_OK: ejecutable correcto.
- HOOK_INSTALLED PlayVariableData::setValue: primer punto activo.
- HOOK_INSTALLED PlayVariableData::requestValue: segundo punto activo.
- FIRST_SET / FIRST_REQUEST: ejemplos reales, sin modificar los valores.
- COUNTERS set/request: numero de llamadas por funcion, con detalle por ID.
- set2047Global / set2047Object: presencia de objeto en variable 2047.
- Si set=0 y request=0 aunque cambie la barra, estas dos rutas tampoco
  observan el medidor. Habra que investigar escrituras directas en memoria.

El ID 2047 representa el medidor de tentacion en el JSON y el objeto UI 49
consulta ese ID. La identidad exacta con la barra Endurance sigue sin demostrar.

## Seguridad y desinstalacion

Solo activa las observaciones si coinciden el SHA256 de player.exe y los
prologos binarios de las funciones. Ninguna variable ni archivo se cambia.
Las pruebas CI validan compilacion y ABI, no prueban el juego real.

Para desinstalar, cierra el juego y elimina solo la version.dll de esta prueba.
El logger no envia datos por Internet; su salida es un fichero local.
