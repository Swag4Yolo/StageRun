# ===============================
# StageRun Compiler Makefile
# ===============================

SHELL := /bin/bash
MAKEFLAGS += -k
# -------- Config --------
VENV := py/compiler_env
PYTHON := python3
PIP := $(VENV)/bin/pip
PYTHON_BIN := $(VENV)/bin/python

PROGRAM := py/stagerun_compiler.py
PROGRAMS_DIR := Programs
LOG_FILE := compiler.log
REQUIREMENTS := py/requirements.txt

# Find all .srun programs recursively
SRUN_FILES := $(shell find $(PROGRAMS_DIR) -type f -name "*.srun")

# Generate corresponding output targets
OUT_FILES := $(SRUN_FILES:.srun=.out.json)

# ===============================
# Default Target
# ===============================

all: clean_log venv compile

# ===============================
# Virtual Environment
# ===============================

venv: $(VENV)/bin/activate

$(VENV)/bin/activate: $(REQUIREMENTS)
	@echo "Initializing virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r $(REQUIREMENTS)
	@touch $(VENV)/bin/activate

# ===============================
# Compilation
# ===============================

compile: $(OUT_FILES)

%.out.json: %.srun venv
	@echo "Compiling $<"
	@out_file="$(@)"; \
	log_file="$(@:.out.json=.log)"; \
	time -p $(PYTHON_BIN) $(PROGRAM) "$<" -o "$$out_file" > "$$log_file" 2>&1

# ===============================
# Cleaning
# ===============================

clean:
	@echo "Removing compiled files..."
	@find $(PROGRAMS_DIR) -type f -name "*.out.json" -delete
	@find $(PROGRAMS_DIR) -type f -name "*.log" -delete

clean_log:
	@rm -f $(LOG_FILE)

distclean: clean
	@echo "Removing virtual environment..."
	@rm -rf $(VENV)

# ===============================
# Logging Wrapper
# ===============================

run:
	@echo "Logging build to $(LOG_FILE)"
	@$(MAKE) all > $(LOG_FILE) 2>&1

# ===============================
# Help
# ===============================

help:
	@echo "Available targets:"
	@echo "  make            -> build everything"
	@echo "  make run        -> build and log to compiler.log"
	@echo "  make clean      -> remove compiled outputs"
	@echo "  make distclean  -> remove outputs and virtualenv"
	@echo "  make help       -> show this help"