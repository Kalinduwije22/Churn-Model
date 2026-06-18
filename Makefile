# ============================================================================
# Makefile — one-word commands for the churn MLOps workflow (venv-based).
#
# Cross-platform: works on Windows cmd, Git Bash, WSL, and Linux. All Python
# commands run inside a project-local virtualenv (.venv), created automatically
# on first use. Housekeeping (stamp file, cleanup, smoke test) runs through
# Python rather than Unix shell tools, so there is no dependency on touch / rm
# / find / curl.
#
#   make install      create .venv + install deps
#   make data         generate the synthetic dataset
#   make train        train the model (writes models/ + MLflow)
#   make serve        run the API locally with reload
#   make test         smoke-test the running API (health + a prediction)
#   make mlflow       open the MLflow experiment UI
#   make docker-build build the serving image locally
#   make docker-run   run the serving image locally on :8000
#   make all          install -> data -> train
#   make deploy       deploy to Azure Container Apps (needs bash + az CLI)
#   make azure-clean  delete the Azure resource group (stop billing)
#   make clean        remove build artifacts (keeps .venv)
#   make clean-venv   remove the virtualenv
#   make distclean    remove everything (artifacts + .venv)
#
# If `python` isn't your interpreter name, override it:  make all PYTHON=python3
# ============================================================================

# System interpreter used to bootstrap the venv (override if needed).
PYTHON ?= python

VENV := .venv

# Pick the right venv layout: Windows uses Scripts/python.exe, Unix uses bin/python.
ifeq ($(OS),Windows_NT)
    PY := $(VENV)/Scripts/python.exe
else
    PY := $(VENV)/bin/python
endif

# Sentinel so deps install once, not on every command.
STAMP := $(VENV)/.installed

IMAGE := churn-api:v1
PORT  := 8000
RG    := rg-churn-demo

.DEFAULT_GOAL := help
.PHONY: help install data train serve test mlflow docker-build docker-run \
        all deploy azure-clean clean clean-venv distclean

help:  ## show this help
	@$(PYTHON) -c "import re,sys; [print('  \033[36m%-14s\033[0m %s' % (m.group(1), m.group(2))) for line in open('Makefile') for m in [re.match(r'([a-zA-Z_-]+):.*?## (.*)', line)] if m]"

# Create the venv only if its interpreter doesn't exist yet.
$(PY):
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

# Install BOTH training and serving deps into the local venv (so you can train
# AND serve locally). The Docker image still uses only requirements-serve.txt.
# Re-runs only if a requirements file changes.
$(STAMP): $(PY) requirements.txt requirements-serve.txt
	$(PY) -m pip install -r requirements.txt -r requirements-serve.txt
	@$(PY) -c "open('$(STAMP)', 'w').close()"

install: $(STAMP)  ## create .venv + install dependencies

data: $(STAMP)  ## generate the synthetic bank-churn dataset
	$(PY) data/generate_data.py

train: data  ## train the model (depends on data)
	$(PY) -m src.train

serve: $(STAMP)  ## run the API locally with auto-reload
	$(PY) -m uvicorn app.main:app --reload --port $(PORT)

test:  ## smoke-test a running local API (no curl needed)
	$(PY) scripts/smoke_test.py $(PORT)

mlflow: $(STAMP)  ## open the MLflow experiment UI
	$(PY) -m mlflow ui --backend-store-uri sqlite:///mlflow.db

docker-build:  ## build the serving image locally
	docker build -t $(IMAGE) .

docker-run:  ## run the serving image locally on :8000
	docker run --rm -p $(PORT):8000 $(IMAGE)

all: install train  ## install + data + train (ready to serve)

deploy:  ## deploy to Azure Container Apps (OS-aware: ps1 on Windows, sh elsewhere)
	$(PY) make.py deploy

azure-clean:  ## delete the Azure resource group (stops billing)
	az group delete --name $(RG) --yes --no-wait

clean:  ## remove build artifacts (keeps .venv)
	$(PYTHON) -c "import shutil, glob, os; [shutil.rmtree(p, ignore_errors=True) for p in ['mlruns', '__pycache__', 'src/__pycache__', 'app/__pycache__', 'scripts/__pycache__']]; [os.remove(f) for g in ['data/*.csv', 'models/*.joblib', 'models/*.json', 'mlflow.db'] for f in glob.glob(g)]"

clean-venv:  ## remove the virtualenv
	$(PYTHON) -c "import shutil; shutil.rmtree('$(VENV)', ignore_errors=True)"

distclean: clean clean-venv  ## remove everything (artifacts + .venv)
