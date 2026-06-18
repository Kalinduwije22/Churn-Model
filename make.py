#!/usr/bin/env python3
"""
make.py — cross-platform task runner (a make replacement that needs no make).

Why this exists: `make` on native Windows cmd fights with forward-slash paths,
missing Unix tools (touch/rm/find), and the Microsoft Store python stub. This
script sidesteps all of that — it is plain Python using the stdlib, so it runs
the same on Windows, WSL, macOS, and Linux.

Usage:
    python make.py <task> [--port 8000]

Tasks:
    install      create .venv + install deps
    data         generate the synthetic dataset
    train        install + data + train the model
    serve        run the API locally with reload
    test         smoke-test a running local API
    mlflow       open the MLflow experiment UI
    docker-build build the serving image
    docker-run   run the serving image on :8000
    all          install + data + train
    clean        remove build artifacts (keeps .venv)
    clean-venv   remove the virtualenv
    distclean    remove everything
    help         list tasks
"""

from __future__ import annotations
import glob
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
STAMP = VENV / ".installed"

# venv interpreter path differs by OS: Windows -> Scripts\python.exe, else bin/python
if os.name == "nt":
    PYEXE = VENV / "Scripts" / "python.exe"
else:
    PYEXE = VENV / "bin" / "python"

PORT = "8000"


def run(cmd: list[str], **kw) -> None:
    """Run a command, printing it first. Raises on failure."""
    print(">>", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def ensure_venv() -> None:
    """Create the venv and install deps once. Idempotent."""
    if not PYEXE.exists():
        print(">> creating virtualenv at .venv")
        # Build the venv with the SAME interpreter running this script —
        # avoids the Store-stub problem entirely (sys.executable is real).
        venv.create(VENV, with_pip=True)
        run([str(PYEXE), "-m", "pip", "install", "--upgrade", "pip"])

    if not STAMP.exists():
        run([str(PYEXE), "-m", "pip", "install",
             "-r", "requirements.txt", "-r", "requirements-serve.txt"])
        STAMP.write_text("")  # stamp so we don't reinstall every run


# ---- tasks -----------------------------------------------------------------

def task_install() -> None:
    ensure_venv()


def task_data() -> None:
    ensure_venv()
    run([str(PYEXE), "data/generate_data.py"])


def task_train() -> None:
    task_data()
    run([str(PYEXE), "-m", "src.train"])


def task_serve() -> None:
    ensure_venv()
    run([str(PYEXE), "-m", "uvicorn", "app.main:app", "--reload", "--port", PORT])


def task_test() -> None:
    ensure_venv()
    run([str(PYEXE), "scripts/smoke_test.py", PORT])


def task_mlflow() -> None:
    ensure_venv()
    run([str(PYEXE), "-m", "mlflow", "ui",
         "--backend-store-uri", "sqlite:///mlflow.db"])


def task_deploy() -> None:
    # Pick the deploy script that matches the OS — no bash needed on Windows.
    if os.name == "nt":
        run(["powershell", "-ExecutionPolicy", "Bypass",
             "-File", "deploy/deploy.ps1"])
    else:
        run(["bash", "deploy/deploy.sh"])


def task_azure_clean() -> None:
    run(["az", "group", "delete", "--name", "rg-churn-demo",
         "--yes", "--no-wait"], shell=(os.name == "nt"))


def task_docker_build() -> None:
    run(["docker", "build", "-t", "churn-api:v1", "."])


def task_docker_run() -> None:
    run(["docker", "run", "--rm", "-p", f"{PORT}:8000", "churn-api:v1"])


def task_all() -> None:
    task_install()
    task_train()


def task_clean() -> None:
    for d in ["mlruns", "__pycache__", "src/__pycache__",
              "app/__pycache__", "scripts/__pycache__"]:
        shutil.rmtree(ROOT / d, ignore_errors=True)
    for pat in ["data/*.csv", "models/*.joblib", "models/*.json", "mlflow.db"]:
        for f in glob.glob(str(ROOT / pat)):
            os.remove(f)
    print("cleaned build artifacts")


def task_clean_venv() -> None:
    shutil.rmtree(VENV, ignore_errors=True)
    print("removed .venv")


def task_distclean() -> None:
    task_clean()
    task_clean_venv()


TASKS = {
    "install": task_install, "data": task_data, "train": task_train,
    "serve": task_serve, "test": task_test, "mlflow": task_mlflow,
    "docker-build": task_docker_build, "docker-run": task_docker_run,
    "all": task_all, "deploy": task_deploy, "azure-clean": task_azure_clean,
    "clean": task_clean, "clean-venv": task_clean_venv,
    "distclean": task_distclean,
}


def task_help() -> None:
    print("Usage: python make.py <task> [--port N]\n\nTasks:")
    for name in TASKS:
        print(f"  {name}")
    print("  help")


def main() -> int:
    global PORT
    args = sys.argv[1:]
    if "--port" in args:
        i = args.index("--port")
        PORT = args[i + 1]
        del args[i:i + 2]

    task = args[0] if args else "help"
    if task in ("help", "-h", "--help"):
        task_help()
        return 0
    fn = TASKS.get(task)
    if fn is None:
        print(f"Unknown task: {task}\n")
        task_help()
        return 1
    try:
        fn()
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nTask '{task}' failed (exit {e.returncode}).")
        return e.returncode


if __name__ == "__main__":
    raise SystemExit(main())
