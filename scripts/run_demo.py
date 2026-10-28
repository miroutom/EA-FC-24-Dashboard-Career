"""One-command Mac setup and launch, using only stdlib before dependencies are installed."""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="Запуск изолированного демо на Mac")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    url = f"http://127.0.0.1:{args.port}"
    try:
        with socket.create_connection(("127.0.0.1", args.port), timeout=0.3):
            try:
                with urllib.request.urlopen(url + "/api/v1/health", timeout=2) as response:
                    health = json.load(response)
                if health.get("demo_mode"):
                    print(f"Демо уже запущено: {url}")
                    if not args.no_browser:
                        webbrowser.open(url)
                    return
            except (OSError, ValueError, urllib.error.URLError):
                pass
            raise SystemExit(f"Порт {args.port} занят другим приложением. Запустите с --port 8002.")
    except (TimeoutError, ConnectionRefusedError):
        pass
    if sys.version_info < (3, 12):
        raise SystemExit("Нужен Python 3.12+")
    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        print("Создаём локальное Python-окружение…", flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    check = subprocess.run(
        [
            str(python),
            "-c",
            ("import fastapi, sqlalchemy, alembic, pydantic_settings, multipart, openpyxl, uvicorn; "
             "from app.core import ROOT; from pathlib import Path; import sys; assert ROOT == Path(sys.argv[1])"),
            str(ROOT),
        ],
        capture_output=True,
        check=False,
    )
    if check.returncode:
        print("Устанавливаем зависимости (первый запуск требует интернета)…", flush=True)
        run([str(python), "-m", "pip", "install", "-r", "backend/requirements.lock"])
        run([str(python), "-m", "pip", "install", "-e", "backend", "--no-deps"])
    frontend = ROOT / "frontend"
    index = frontend / "dist" / "index.html"
    sources = [
        frontend / "package.json",
        frontend / "package-lock.json",
        frontend / "vite.config.ts",
        frontend / "index.html",
        *list((frontend / "src").rglob("*")),
    ]
    needs_build = not index.exists() or any(
        p.is_file() and p.stat().st_mtime > index.stat().st_mtime for p in sources
    )
    if needs_build:
        npm, node = shutil.which("npm"), shutil.which("node")
        if not npm or not node:
            raise SystemExit("Для первой сборки нужен Node.js 22+ (включая npm).")
        major = int(subprocess.check_output([node, "--version"], text=True).strip().lstrip("v").split(".")[0])
        if major < 22:
            raise SystemExit("Для сборки нужен Node.js 22+")
        installed_lock = frontend / "node_modules" / ".package-lock.json"
        if (
            not installed_lock.exists()
            or (frontend / "package-lock.json").stat().st_mtime > installed_lock.stat().st_mtime
        ):
            run([npm, "--prefix", "frontend", "ci", "--no-audit", "--no-fund"])
        run([npm, "--prefix", "frontend", "run", "build"])
    print(f"ДЕМО: синтетические данные, отдельная база data-demo. Открываем {url}", flush=True)
    command = [str(python), "-m", "app.demo", "--port", str(args.port)]
    if args.no_browser:
        command.append("--no-browser")
    os.execv(str(python), command)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
