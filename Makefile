PYTHON := ./venv/bin/python

# ----------------------------------------
# Install
# ----------------------------------------
.PHONY: install install-debug reinstall

install:
	@echo "\033[1;32m🚀 Installing Minitrino, test packages, and dev dependencies...\033[0m"
	@./install/src/install.sh
	@echo "\033[1;32m✅ Installation complete.\033[0m"

install-debug:
	@echo "\033[1;34m🐞 Debug Install: Verbose mode enabled.\033[0m"
	@./install/src/install.sh -v
	@echo "\033[1;32m✅ Installation complete.\033[0m"

reinstall:
	@echo "\033[1;34m🗑️  Removing existing virtual environment...\033[0m"
	@rm -rf venv
	@echo "\033[1;34m🚀 Reinstalling Minitrino, test packages, and dev dependencies...\033[0m"
	@./install/src/install.sh -v
	@echo "\033[1;32m✅ Installation complete.\033[0m"

# ----------------------------------------
# Pre-commit
# ----------------------------------------
.PHONY: pre-commit
pre-commit:
	@echo "\033[1;32m🚀 Running pre-commit...\033[0m"
	@$(PYTHON) -m pre_commit run --all-files --verbose &> .local/pre-commit.log || \
		{ \
			echo "\033[1;31m❌ Pre-commit failed, log stored at .local/pre-commit.log\033[0m"; \
			exit 1; \
		}
	@echo "\033[1;32m✅ Pre-commit run successfully, log stored at .local/pre-commit.log\033[0m"

# ----------------------------------------
# Docs
# ----------------------------------------
.PHONY: docs docs-up docs-down

docs:
	docker compose -f install/docs/docker-compose.yml \
		run --rm minitrino-docs-build
	@echo "\033[1;32m✅ Docs built successfully\033[0m"

docs-up: docs
	docker compose -f install/docs/docker-compose.yml up -d
	@echo "\033[1;32m✅ Docs server started at http://localhost:8000\033[0m"

docs-down:
	docker compose -f install/docs/docker-compose.yml down --timeout 0
	@echo "\033[1;32m🛑 Docs server stopped\033[0m"
