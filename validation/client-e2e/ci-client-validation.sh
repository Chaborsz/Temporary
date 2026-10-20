#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(pwd)"
VALIDATION_SOURCE_DIR="${GITHUB_WORKSPACE:?}/validation/client-e2e"
CI_VALIDATION_DIR="${ARTIFACT_DIR:?}/client"
export CI_VALIDATION_DIR
mkdir -p "$CI_VALIDATION_DIR" "$PROJECT_DIR/ci-validation/src/main/java/validation"
cp "$VALIDATION_SOURCE_DIR/CiClientValidation.java" "$PROJECT_DIR/ci-validation/src/main/java/validation/"

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

python3 - "$PROJECT_DIR/build/resources/main/fabric.mod.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding='utf-8') as handle:
    metadata = json.load(handle)
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

set +e
timeout "${CLIENT_TIMEOUT_SECONDS:-900}s" gradle --no-daemon --no-build-cache --stacktrace \
  -x classes -x processResources runClient > "$CI_VALIDATION_DIR/runClient-console.log" 2>&1 &
client_pid=$!
set -e
cleanup() {
  pkill -TERM -f '[n]et.minecraft.client.main.Main' 2>/dev/null || true
  kill "$client_pid" 2>/dev/null || true
  sleep 2
  pkill -KILL -f '[n]et.minecraft.client.main.Main' 2>/dev/null || true
}
trap cleanup EXIT

python3 "$VALIDATION_SOURCE_DIR/capture_client_evidence.py" \
  --watch --trace "$CI_VALIDATION_DIR/runtime-trace.log" --output "$CI_VALIDATION_DIR" &
watcher_pid=$!

python3 "$VALIDATION_SOURCE_DIR/drive_minecraft_ui.py" \
  --trace "$CI_VALIDATION_DIR/runtime-trace.log" \
  --screenshots "$CI_VALIDATION_DIR"

deadline=$((SECONDS + ${CLIENT_TIMEOUT_SECONDS:-900}))
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

python3 "$VALIDATION_SOURCE_DIR/capture_client_evidence.py" \
  --trace "$CI_VALIDATION_DIR/runtime-trace.log" --output "$CI_VALIDATION_DIR"
wait "$watcher_pid" || watcher_rc=$?
if [[ "${watcher_rc:-0}" -gt 1 ]]; then
  echo "Swing frame capture did not finish with the integrated combat scenario." >&2
  exit 64
fi

sha256sum "$PROJECT_DIR"/build/libs/*.jar > "$CI_VALIDATION_DIR/product-jars-after-client.txt"
cmp "$CI_VALIDATION_DIR/product-jars-before-client.txt" "$CI_VALIDATION_DIR/product-jars-after-client.txt"
echo "PRODUCT_JAR_UNMODIFIED_BY_CI_HARNESS=PASS"
echo "CLIENT_OWNER_DEFENSE_E2E=PASS"
