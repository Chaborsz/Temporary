# Prueba reversible de Endurance - ID 2047

Tipo: candidata experimental, no validada en el juego.
Objetivo: impedir los incrementos del medidor de tentacion/excitacion 2047.
El cambio no modifica HP, MP, ID2003, ID2386, ID2054 ni player.exe.

## Artefacto

Workflow: https://github.com/Chaborsz/Temporary/actions/workflows/endurance-freeze2047-test.yml

Solo instalar cuando el workflow termine con SUCCESS y conste CBC_ROUNDTRIP_PASS.
El artefacto Endurance-2047-freeze0-TEST-<RUN_ID> incluye un ZIP con
project.json ya cifrado para el motor. No necesitas Python ni descifrarlo.

## Instalacion y vuelta atras en Windows

1. Cierra el juego; haz copia de la partida guardada.
2. Abre la carpeta del juego Resources\data y encuentra project.json (cifrado).
3. Comprueba que el original ocupa exactamente 301.997.028 bytes.
   Si el tamaño es diferente, NO instales el candidato: puede ser otra version.
4. Copia el original fuera de la carpeta del juego y conservalo como
   project.json.ORIGINAL.bak. No borres la copia.
5. Descarga el artefacto SUCCESS de GitHub Actions. Extrae el ZIP externo y
   despues endurance_2047_freeze0_TEST.zip para obtener project.json cifrado.
6. Sustituye exclusivamente Resources\data\project.json y arranca el juego.
7. En una partida de prueba comprueba la barra Endurance situada bajo HP y MP.
   No uses tu unica partida guardada.
8. Si falla alguna transicion, el HUD o el inicio, cierra el juego y restaura
   el original con el nombre exacto project.json.

## Limitaciones

Las acciones que aumentan la tentacion se sustituyen por asignaciones a cero
de ID2047. Algunas escenas podrian necesitar ese avance a 75/76 para continuar.
Una partida guardada puede restaurar un valor previo hasta la siguiente escritura.
La identidad con el rotulo exacto Endurance no fue comprobada visualmente.
No hay pruebas de ejecucion real del juego ni de jugabilidad. Es EXPERIMENTAL.

Fuente: Forest of the Blue Skin JSON descifrado de 301.997.021 bytes.
SHA256: 2a19596ffc6e54c4651780ad9ee0ab37dc98d4b6a0a979d63ec2b32523e1af89
