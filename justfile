@_default:
    just --list --unsorted

@_checks: check-python check-unused check-security check-spelling check-commits
@_tests: test-python
@_builds: build-contributors build-website build-readme

# Run all build-related recipes in the justfile
run-all: install-deps update-quarto-theme format-python _checks _tests _builds

# List all TODO items in the repository
list-todos:
  grep -R -n \
    --exclude="*.code-snippets" \
    --exclude-dir=.quarto \
    --exclude=justfile \
    --exclude=_site \
    "TODO" *

# Install the pre-commit hooks
install-precommit:
  # Install pre-commit hooks
  uvx pre-commit install
  # Run pre-commit hooks on all files
  uvx pre-commit run --all-files
  # Update versions of pre-commit hooks
  uvx pre-commit autoupdate
# Update the Quarto seedcase-theme extension
update-quarto-theme:
  # Add theme if it doesn't exist, update if it does
  quarto update seedcase-project/seedcase-theme --no-prompt

# Install Python package dependencies
install-deps:
  uv sync --all-extras --dev --upgrade

# Run the Python tests
test-python:
  uv run pytest
  # Make the badge from the coverage report
  uv run genbadge coverage \
    -i coverage.xml \
    -o htmlcov/coverage.svg

# Check Python code for any errors that need manual attention
check-python:
  # Check formatting
  uv run ruff check .
  # Check types
  uv run mypy .

# Reformat Python code to match coding style and general structure
format-python:
  uv run ruff check --fix .
  uv run ruff format .

# Build the documentation website using Quarto
build-website:
  # To let Quarto know where python is.
  export QUARTO_PYTHON=.venv/bin/python3
  # Delete any previously built files from quartodoc.
  # -f is to not give an error if the files don't exist yet.
  rm -rf docs/reference
  uv run quartodoc build
  uv run quarto render --execute

# Check the commit messages on the current branch that are not on the main branch
check-commits:
  #!/usr/bin/env bash
  branch_name=$(git rev-parse --abbrev-ref HEAD)
  number_of_commits=$(git rev-list --count HEAD ^main)
  if [[ ${branch_name} != "main" && ${number_of_commits} -gt 0 ]]
  then
    # If issue happens, try `uv tool update-shell`
    uvx --from commitizen cz check --rev-range main..HEAD
  else
    echo "On 'main' or current branch doesn't have any commits."
  fi

# Run basic security checks on the package
check-security:
  uv run bandit -r src/

# Check for spelling errors in files
check-spelling:
  uv run typos

# Build the documentation as PDF using Quarto
build-pdf:
  # To let Quarto know where python is.
  export QUARTO_PYTHON=.venv/bin/python3
  uv run quarto install tinytex
  # For generating images from Mermaid diagrams
  uv run quarto install chromium
  uv run quarto render --profile pdf --to pdf
  find docs -name "mermaid-figure-*.png" -delete

# Check for unused code in the package and its tests
check-unused:
  # exit code=0: No unused code was found
  # exit code=3: Unused code was found
  # Three confidence values:
  # - 100 %: function/method/class argument, unreachable code
  # - 90 %: import
  # - 60 %: attribute, class, function, method, property, variable
  # There are some things should be ignored though, with the allowlist.
  # Create an allowlist with `vulture --make-allowlist`
  uv run vulture src/ tests/ **/vulture-allowlist.py

# Re-build the README file from the Quarto version
build-readme:
  uvx --from quarto quarto render README.qmd --to gfm

# Generate a Quarto include file with the contributors
build-contributors:
  sh ./tools/get-contributors.sh seedcase-project/check-datapackage > docs/includes/_contributors.qmd

# Check for and apply updates from the template
update-from-template:
  # Do not update existing source files
  uvx copier update --trust --defaults $(find src/check_datapackage -type f -printf "--exclude %p ")

# Reset repo changes to match the template
reset-from-template:
  uvx copier recopy --trust --defaults
