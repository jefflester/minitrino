# Fail recipes when any command in a pipeline fails (e.g., `cmd | tee log`).
# Flags are set on SHELL because .SHELLFLAGS is unsupported in GNU Make 3.81
# (macOS default).
SHELL := /bin/bash -o pipefail

PYTHON ?= ./venv/bin/python

# ----------------------------------------
# Install
# ----------------------------------------
.PHONY: install install-debug reinstall

install:
	@printf '%b\n' "\033[1;32m🚀 Installing Minitrino, test packages, and dev dependencies...\033[0m"
	@./install/src/install.sh
	@printf '%b\n' "\033[1;32m✅ Installation complete.\033[0m"

install-debug:
	@printf '%b\n' "\033[1;34m🐞 Debug Install: Verbose mode enabled.\033[0m"
	@./install/src/install.sh -v
	@printf '%b\n' "\033[1;32m✅ Installation complete.\033[0m"

reinstall:
	@printf '%b\n' "\033[1;34m🗑️  Removing existing virtual environment...\033[0m"
	@rm -rf venv
	@printf '%b\n' "\033[1;34m🚀 Reinstalling Minitrino, test packages, and dev dependencies...\033[0m"
	@./install/src/install.sh -v
	@printf '%b\n' "\033[1;32m✅ Installation complete.\033[0m"

# ----------------------------------------
# Pre-commit
# ----------------------------------------
.PHONY: pre-commit
pre-commit:
	@printf '%b\n' "\033[1;32m🚀 Running pre-commit...\033[0m"
	@mkdir -p .local
	@$(PYTHON) -m pre_commit run --all-files --verbose 2>&1 | tee .local/pre-commit.log || \
		{ \
			printf '%b\n' "\033[1;31m❌ Pre-commit failed, log stored at .local/pre-commit.log\033[0m"; \
			exit 1; \
		}
	@printf '%b\n' "\033[1;32m✅ Pre-commit run successfully, log stored at .local/pre-commit.log\033[0m"

# ----------------------------------------
# Docs
# ----------------------------------------
.PHONY: docs docs-up docs-down

docs:
	docker compose -f install/docs/docker-compose.yaml \
		run --rm minitrino-docs-build
	@printf '%b\n' "\033[1;32m✅ Docs built successfully\033[0m"

docs-up: docs
	docker compose -f install/docs/docker-compose.yaml up -d
	@printf '%b\n' "\033[1;32m✅ Docs server started at http://localhost:8000\033[0m"

docs-down:
	docker compose -f install/docs/docker-compose.yaml down --timeout 0
	@printf '%b\n' "\033[1;32m🛑 Docs server stopped\033[0m"

# ----------------------------------------
# Tests
# ----------------------------------------
.PHONY: lib-tests integration-tests unit-tests coverage all-tests

# ARGS passes in modules to test
lib-tests:
	@printf '%b\n' "\033[1;32m🚀 Running lib tests\033[0m"
	@mkdir -p .local
	@LIC_PATH=$(LIC_PATH) \
	$(PYTHON) -m src.tests.lib.runner -x \
		--debug --image starburst ${ARGS} 2>&1 | tee .local/lib-test.log || \
		{ \
			printf '%b\n' "\033[1;31m❌ Lib tests failed, log stored at .local/lib-test.log\033[0m"; \
			exit 1; \
		}
	@printf '%b\n' "\033[1;32m✅ Lib tests completed, log stored at .local/lib-test.log\033[0m"

# FF=1 to run last failed tests first, then continue with all tests
integration-tests:
	@printf '%b\n' "\033[1;32m🚀 Running integration tests\033[0m"
	@mkdir -p .local
	@pytest \
		-x $(if $(FF),--ff,) \
		-s -vvv --log-level=DEBUG --tb=short \
		src/tests/cli/integration_tests 2>&1 | tee .local/pytest.log || \
		{ \
			printf '%b\n' "\033[1;31m❌ Integration tests failed, log stored at .local/pytest.log\033[0m"; \
			exit 1; \
		}
	@printf '%b\n' "\033[1;32m✅ Integration tests completed, log stored at .local/pytest.log\033[0m"

# Run unit tests with coverage
unit-tests:
	@printf '%b\n' "\033[1;32m🚀 Running unit tests\033[0m"
	@mkdir -p .local
	@pytest \
		-x $(if $(FF),--ff,) \
		-s -vv --log-level=DEBUG --tb=short \
		--cov=minitrino --cov-report=term-missing \
		src/tests/cli/unit_tests 2>&1 | tee .local/unit-test.log || \
		{ \
			printf '%b\n' "\033[1;31m❌ Unit tests failed, log stored at .local/unit-test.log\033[0m"; \
			exit 1; \
		}
	@printf '%b\n' "\033[1;32m✅ Unit tests completed, log stored at .local/unit-test.log\033[0m"

# Generate coverage report
coverage:
	@printf '%b\n' "\033[1;32m📊 Generating coverage report\033[0m"
	@mkdir -p .local
	@pytest \
		--cov=minitrino \
		--cov-report=html \
		--cov-report=term-missing:skip-covered \
		--cov-fail-under=90 \
		src/tests/cli/unit_tests 2>&1 | tee .local/coverage.log || \
		{ \
			printf '%b\n' "\033[1;31m❌ Coverage below 90%, see .local/coverage.log\033[0m"; \
			exit 1; \
		}
	@printf '%b\n' "\033[1;32m✅ Coverage report generated at htmlcov/index.html\033[0m"

# Run all test suites
all-tests: unit-tests integration-tests lib-tests
	@printf '%b\n' "\033[1;32m✅ All tests completed successfully\033[0m"
