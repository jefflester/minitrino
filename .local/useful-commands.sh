# Remove trailing whitespace
find . -name "*.yaml" -type f -exec sed -i '' 's/[[:space:]]*$//' {} +
find . -name "*.yaml" -type f -exec awk 'length($0) > 80 { print FILENAME ":" NR ": " $0 }' {} +

# Run pre-commit
pre-commit run --all-files --verbose &> .local/pre-commit.log

# Run mypy
mypy src/ &> .local/mypy.log

# Run pydocstyle
pydocstyle src/ &> .local/pydocstyle.log

# Run all; pick up from last failed test
pytest -s -x -v --tb=short src/test/cli/ &> .local/pytest.log

# Run entire test script - add -x to stop on first failure
pytest \
    -x --lf \
    -s -vvv --log-level=DEBUG --tb=short \
    src/test/cli/test_cmd_provision.py &> .local/pytest.log

# Run entire test - add -x to stop on first failure
pytest --log-level=INFO \
    -vvv \
    --tb=short \
    src/test/cli/test_cmd_provision.py::test_version_scenarios &> .local/pytest.log

# Specify a test function
pytest --log-level=INFO \
    -vvv \
    --tb=short \
    src/test/cli/test_cmd_provision.py::test_enterprise_scenarios &> .local/enterprise.log

minitrino -v \
    -e cluster_ver=468-e \
    -e config_properties=$'starburst.access-control.audit.access-log.enabled=true\nstarburst.access-control.audit.access-log.queue-size=100' \
    -e lic_path=~/work/license/starburstdata.license \
    provision -m insights -m biac -i starburst --docker-native --build
