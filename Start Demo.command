#!/bin/bash
set -euo pipefail
LCA_PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$LCA_PROJECT_DIR"
if [[ -x "$LCA_PROJECT_DIR/.venv/bin/python" ]]; then
    exec "$LCA_PROJECT_DIR/.venv/bin/python" "$LCA_PROJECT_DIR/scripts/run_demo.py" "$@"
fi
for LCA_PYTHON in python3.12 python3.13 python3.14 python3; do
    if command -v "$LCA_PYTHON" >/dev/null 2>&1 && "$LCA_PYTHON" -c 'import sys; assert sys.version_info >= (3,12)' >/dev/null 2>&1; then
        exec "$LCA_PYTHON" "$LCA_PROJECT_DIR/scripts/run_demo.py" "$@"
    fi
done
echo 'Нужен Python 3.12 или новее. Установите Python и запустите Start Demo.command снова.'
read -r -p 'Нажмите Enter, чтобы закрыть окно…' _
exit 1
