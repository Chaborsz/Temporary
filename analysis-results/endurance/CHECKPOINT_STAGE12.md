# Endurance — checkpoint Stage12: diagnostico de escritores AGTK

## Evidencia del usuario
EnduranceDiagnostic.log con SOURCE_OK + HOOK_INSTALLED pero:
- COUNTERS total=0 id2047=0 global2047=0 object2047=0 id2003=0 id2386=0 id2054=0 other=0
- Repetido sin cambios durante la prueba.
**Conclusion:** el hook anterior en GameManager::assignVariableData (RVA 0x1E8760) no observo llamadas. No demuestra que 2047 sea el medidor incorrecto.

## Audit del ejecutable (solo lectura)
player.exe original: 8.757.760 bytes; SHA256 02a59baab7a4c941f9a01f485082396d61e750a41dc955cff895bef5395441ea
- 0x0046AB90 / RVA 0x6AB90: PlayVariableData metodo de actualizacion de valor, inicial 55 8B EC 83 E4 F8; 12 llamadas estaticas directas.
- 0x0046ACB0 / RVA 0x6ACB0: PlayVariableData::requestValue, inicial 55 8B EC F2 0F 10 45 08, sin llamadas estaticas directas.
- 0x005E8760 / RVA 0x1E8760: GameManager::assignVariableData, 0 llamadas estaticas directas detectadas.
- RVA 0x6AB90 devuelve double (x87), requestValue recibe double + float y devuelve void.
- Fuente: cheats/endurance/dll/audit_variable_writers.py
- CI audit: https://github.com/Chaborsz/Temporary/actions/runs/42126584660

## Nueva DLL diagnostica Stage12
- Codigo: cheats/endurance/dll/endurance_writers_diagnostic.cpp
- Proxy: version.dll PE32 x86.
- **NO cambia ningun valor del juego.** Registra eventos de setValue/requestValue para 2047, 2003, 2386, 2054 y otros.
- Log: EnduranceWriters.log junto a player.exe.
- ABI verificado con 10/10 llamadas de test preservando valores; 10 exports de version.dll; comprobacion de hash original; prologos de las 2 funciones verificadas.
- Workflow: https://github.com/Chaborsz/Temporary/actions/runs/42127076992 SUCCESS.
- Artefacto: https://github.com/Chaborsz/Temporary/actions/runs/42127076992/artifacts/13460938624
- Nombre: Endurance-Stage12-Writers-Diagnostic-x86-42127076992
- Documentacion: cheats/endurance/dll/README_WRITERS.md

## Proxima comprobacion del usuario
Cerrar el juego, quitar la version.dll vieja, conservar project.json original.
Copiar la version.dll de Stage12 junto a player.exe.
Provocar cambio visible en la barra del corazon bajo LIFE/MP. Enviar EnduranceWriters.log.

Interpretacion:
- set o request positivo y 2047 positivo: ruta y candidato a correlacionar.
- set/request positivos para 2003 u otra variable: investigar correspondencia temporal, no forzar ID 2047.
- set=request=0 con movimiento del HUD: el motor usa rutas no interceptadas (posibles escrituras directas a PlayVariableData +0x28; investigar xrefs).
- HOOK_FAILED: falló la instalación; no modificar ninguna variable.

El entorno local CAAS devolvio ClientError al intentar listar /mnt/data, por lo cual la compilacion MSVC se realizo en GitHub Actions. Biblioteca sigue siendo fuente preferida; GitHub es herramienta de compilacion alternativa.

No declarada una DLL funcional de Endurance. Esta es solo una auditoria instrumental.
