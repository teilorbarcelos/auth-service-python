#!/usr/bin/env bash
set -uo pipefail

PROJECT_KEY="${1:-auth-service-python}"
PROJECT_NAME="${2:-Auth Service Python}"
SONAR_TOKEN="${SONAR_TOKEN:-squ_733ffb0b40e059b7a5f353a7f16c2896cb8e7052}"
SONAR_HOST="${SONAR_HOST:-http://localhost:9000}"
SCANNER_BIN="${SCANNER_BIN:-/home/teilor/.sonar/native-sonar-scanner/sonar-scanner-6.2.1.4610-linux-x64/bin/sonar-scanner}"

export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="./venv/bin:$PATH"

echo "=========================================="
echo " SonarQube scan"
echo "  Project:    $PROJECT_KEY"
echo "  Name:       $PROJECT_NAME"
echo "=========================================="

rm -rf .sonarqube
rm -f coverage.xml

echo ""
echo ">> Step 1/2: Tests + Coverage"
python3 -m pytest --cov=src --cov-report=xml --cov-report=term-missing tests/ || echo "WARN: tests reported failures"
set -e

echo ""
echo ">> Step 2/2: SonarQube scan"
if [ -f "coverage.xml" ]; then
  rm -rf .sonarqube
  "$SCANNER_BIN" \
    -Dsonar.host.url="$SONAR_HOST" \
    -Dsonar.token="$SONAR_TOKEN" \
    -Dsonar.projectKey="$PROJECT_KEY" \
    -Dsonar.projectName="$PROJECT_NAME" \
    -Dsonar.sources="src" \
    -Dsonar.tests="tests" \
    -Dsonar.exclusions="**/venv/**,**/migrations/**,**/storage/**,**/scripts/**,**/infra/**" \
    -Dsonar.python.coverage.reportPaths="coverage.xml" || echo "WARN: scanner failed (exit $?)"
else
  echo "WARN: coverage.xml not found; skipping coverage injection"
fi

echo ""
echo "=========================================="
echo " Done. Dashboard:"
echo "  $SONAR_HOST/dashboard?id=$PROJECT_KEY"
echo "=========================================="
