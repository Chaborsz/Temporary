#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(pwd)"
VALIDATION_SOURCE_DIR="${GITHUB_WORKSPACE:?}/validation/client-e2e"
CI_VALIDATION_DIR="${ARTIFACT_DIR:?}/client"
export CI_VALIDATION_DIR
mkdir -p "$CI_VALIDATION_DIR" "$PROJECT_DIR/ci-validation/src/main/java/validation"
cp "$VALIDATION_SOURCE_DIR/CiClientValidation.java" "$PROJECT_DIR/ci-validation/src/main/java/validation/"
mkdir -p "$PROJECT_DIR/ci-validation/src/main/java/validation/mixin"
cp "$VALIDATION_SOURCE_DIR/ClientSwingTraceMixin.java" "$PROJECT_DIR/ci-validation/src/main/java/validation/mixin/"

cat > "$PROJECT_DIR/ci-validation/init.gradle" <<'GRADLE'
import org.gradle.api.tasks.compile.JavaCompile

gradle.projectsEvaluated {
    def p = gradle.rootProject
    p.tasks.register('ciCompileClientHarness', JavaCompile) {
        source = p.fileTree('ci-validation/src/main/java') { include '**/*.java' }
        classpath = p.files(p.sourceSets.main.compileClasspath, p.sourceSets.main.output)
        destinationDirectory = p.layout.buildDirectory.dir('ci-validation/classes')
        options.encoding = 'UTF-8'
        options.release = 17
    }
}
GRADLE

gradle --no-daemon --no-build-cache --stacktrace -I ci-validation/init.gradle ciCompileClientHarness \
  2>&1 | tee "$CI_VALIDATION_DIR/harness-compile.log"
cp -a "$PROJECT_DIR/build/ci-validation/classes/." "$PROJECT_DIR/build/classes/java/main/"

cat > "$PROJECT_DIR/build/resources/main/ci_swing_trace.mixins.json" <<'JSON'
{
  "required": true,
  "package": "validation.mixin",
  "compatibilityLevel": "JAVA_17",
  "client": ["ClientSwingTraceMixin"],
  "injectors": {"defaultRequire": 1}
}
JSON

python3 - "$PROJECT_DIR/build/resources/main/fabric.mod.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding='utf-8') as handle:
    metadata = json.load(handle)
mixins = metadata.setdefault('mixins', [])
if 'ci_swing_trace.mixins.json' not in mixins:
    mixins.append('ci_swing_trace.mixins.json')
entrypoints = metadata.setdefault('entrypoints', {})
for environment in ('main', 'client'):
    current = entrypoints.setdefault(environment, [])
    if 'validation.CiClientValidation' not in current:
        current.append('validation.CiClientValidation')
with open(path, 'w', encoding='utf-8') as handle:
    json.dump(metadata, handle, indent=2, ensure_ascii=False)
    handle.write('\n')
PY

sha256sum "$PROJECT_DIR"/build/libs/*.jar > "$CI_VALIDATION_DIR/product-jars-before-client.txt"

watcher_pid=""
phase_watcher_pid=""
set +e
setsid timeout "${CLIENT_TIMEOUT_SECONDS:-900}s" gradle --no-daemon --no-build-cache --stacktrace \
  -x classes -x processResources runClient > "$CI_VALIDATION_DIR/runClient-console.log" 2>&1 &
client_pid=$!
set -e
cleanup() {
  rc=$?
  trap - EXIT
  if [[ "$rc" -ne 0 ]]; then
    echo "=== CLIENT HARNESS DIAGNOSTICS ===" >&2
    tail -160 "$CI_VALIDATION_DIR/runClient-console.log" >&2 || true
    cat "$CI_VALIDATION_DIR/runtime-trace.log" >&2 || true
    find "$CI_VALIDATION_DIR" -maxdepth 1 -type f -printf '%f %s bytes\\n' >&2 || true
  fi
  if [[ -n "$watcher_pid" ]]; then kill "$watcher_pid" 2>/dev/null || true; wait "$watcher_pid" 2>/dev/null || true; fi
  if [[ -n "$phase_watcher_pid" ]]; then kill "$phase_watcher_pid" 2>/dev/null || true; wait "$phase_watcher_pid" 2>/dev/null || true; fi
  kill -TERM -- "-$client_pid" 2>/dev/null || true
  pkill -TERM -f '[n]et.fabricmc.devlaunchinjector.Main' 2>/dev/null || true
  pkill -TERM -f '[n]et.minecraft.client.main.Main' 2>/dev/null || true
  kill "$client_pid" 2>/dev/null || true
  sleep 2
  kill -KILL -- "-$client_pid" 2>/dev/null || true
  pkill -KILL -f '[n]et.fabricmc.devlaunchinjector.Main' 2>/dev/null || true
  pkill -KILL -f '[n]et.minecraft.client.main.Main' 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT

launch_deadline=$((SECONDS + 180))
launched=0
while (( SECONDS < launch_deadline )); do
  if grep -Eiq '(LWJGL|OpenGL|Reloading ResourceManager|Setting user:|Backend library|Sound engine started|Created: [0-9]+x[0-9]+)' "$CI_VALIDATION_DIR/runClient-console.log" 2>/dev/null; then
    launched=1
    break
  fi
  latest_log="$(find "$PROJECT_DIR" -type f -path '*/logs/latest.log' -print -quit 2>/dev/null || true)"
  if [[ -n "$latest_log" ]] && grep -Eiq '(LWJGL|OpenGL|Reloading ResourceManager|Setting user:|Backend library|Sound engine started|Created: [0-9]+x[0-9]+)' "$latest_log"; then
    launched=1
    break
  fi
  if ! kill -0 "$client_pid" 2>/dev/null; then
    echo "runClient exited before the client reached a graphical screen." >&2
    tail -160 "$CI_VALIDATION_DIR/runClient-console.log" >&2 || true
    exit 65
  fi
  sleep 2
done
if [[ "$launched" != "1" ]]; then
  echo "No graphical client launch marker observed after 180 seconds." >&2
  exit 66
fi

python3 "$VALIDATION_SOURCE_DIR/capture_client_evidence.py" \
  --watch --trace "$CI_VALIDATION_DIR/runtime-trace.log" --output "$CI_VALIDATION_DIR" &
watcher_pid=$!
python3 "$VALIDATION_SOURCE_DIR/capture_client_evidence.py" \
  --phase-watch --trace "$CI_VALIDATION_DIR/runtime-trace.log" --output "$CI_VALIDATION_DIR" &
phase_watcher_pid=$!

UI_TIMEOUT_SECONDS=300 python3 "$VALIDATION_SOURCE_DIR/drive_minecraft_ui.py" \
  --trace "$CI_VALIDATION_DIR/runtime-trace.log" \
  --screenshots "$CI_VALIDATION_DIR"

deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  if grep -q 'CI_OWNER_DEFENSE_E2E_PASS' "$CI_VALIDATION_DIR/runtime-trace.log" 2>/dev/null; then
    break
  fi
  if grep -q 'CI_OWNER_DEFENSE_E2E_FAIL' "$CI_VALIDATION_DIR/runtime-trace.log" 2>/dev/null; then
    cat "$CI_VALIDATION_DIR/runtime-trace.log"
    exit 61
  fi
  if ! kill -0 "$client_pid" 2>/dev/null; then
    echo "runClient exited before the integrated owner-defense chain passed." >&2
    tail -200 "$CI_VALIDATION_DIR/runClient-console.log" >&2 || true
    exit 62
  fi
  sleep 1
done
grep -q 'CI_OWNER_DEFENSE_E2E_PASS' "$CI_VALIDATION_DIR/runtime-trace.log" || {
  echo "Timed out waiting for a real owner-damage → Companion response → melee pass." >&2
  cat "$CI_VALIDATION_DIR/runtime-trace.log" >&2 || true
  exit 63
}

wait "$watcher_pid" || watcher_rc=$?
watcher_pid=""
wait "$phase_watcher_pid" || phase_watcher_rc=$?
phase_watcher_pid=""
if [[ "${phase_watcher_rc:-0}" -ne 0 ]]; then
  echo "Named swing render-phase screenshots did not complete." >&2
  exit 64
fi
if [[ "${watcher_rc:-0}" -gt 1 ]]; then
  echo "Swing frame capture did not finish with the integrated combat scenario." >&2
  exit 64
fi

# Serialize the HUD commands after all attack-view commands so the two
# screenshot drivers cannot type into the same in-game chat at once.
python3 "$VALIDATION_SOURCE_DIR/capture_client_evidence.py" \
  --trace "$CI_VALIDATION_DIR/runtime-trace.log" --output "$CI_VALIDATION_DIR"

sha256sum "$PROJECT_DIR"/build/libs/*.jar > "$CI_VALIDATION_DIR/product-jars-after-client.txt"
cmp "$CI_VALIDATION_DIR/product-jars-before-client.txt" "$CI_VALIDATION_DIR/product-jars-after-client.txt"
echo "PRODUCT_JAR_UNMODIFIED_BY_CI_HARNESS=PASS"
echo "CLIENT_OWNER_DEFENSE_E2E=PASS"
