.PHONY: docs

docs:
	rm -rf docs/api
	sphinx-apidoc -o docs/api src/cli/minitrino -f -e
	sphinx-build -b html docs docs/_build/html
