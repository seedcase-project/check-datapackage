

<!-- NOTE: This README.md is auto-generated from README.qmd. Edit that file. -->

<p align="center">
    <a href="https://check-datapackage.seedcase-project.org/">
        <img src="https://raw.githubusercontent.com/seedcase-project/check-datapackage/main/_extensions/seedcase-project/seedcase-theme/logos/navbar-logo-check-datapackage.svg" alt="Link to Sprout website" height="150"/>
    </a>
</p>

# check-datapackage: Ensure the compliance of your Data Package metadata

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17733655.svg)](https://doi.org/10.5281/zenodo.17733655)
[![PyPI
Version](https://img.shields.io/pypi/v/check-datapackage.svg)](https://pypi.org/project/check-datapackage/)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-teal.json?raw=true.svg)](https://github.com/copier-org/copier)
[![Python Version from PEP 621
TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/seedcase-project/check-datapackage/refs/heads/main/pyproject.toml)](https://github.com/seedcase-project/check-datapackage/blob/main/pyproject.toml)
[![GitHub
License](https://img.shields.io/github/license/seedcase-project/check-datapackage.svg)](https://github.com/seedcase-project/check-datapackage/blob/main/LICENSE.md)
[![GitHub
Release](https://img.shields.io/github/v/release/seedcase-project/check-datapackage.svg)](https://github.com/seedcase-project/check-datapackage/releases/latest)
[![Build
documentation](https://github.com/seedcase-project/check-datapackage/actions/workflows/build-website.yml/badge.svg)](https://github.com/seedcase-project/check-datapackage/actions/workflows/build-website.yml)
[![Check
package](https://github.com/seedcase-project/check-datapackage/actions/workflows/check-package.yml/badge.svg)](https://github.com/seedcase-project/check-datapackage/actions/workflows/check-package.yml)
[![OpenSSF
Scorecard](https://api.scorecard.dev/projects/github.com/seedcase-project/check-datapackage/badge?raw=true.svg)](https://scorecard.dev/viewer/?uri=github.com/seedcase-project/check-datapackage)
[![CodeQL](https://github.com/seedcase-project/check-datapackage/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/seedcase-project/check-datapackage/actions/workflows/github-code-scanning/codeql)
[![code
coverage](https://raw.githubusercontent.com/seedcase-project/check-datapackage/coverage/coverage.svg?raw=true)](https://htmlpreview.github.io/?https://raw.githubusercontent.com/seedcase-project/check-datapackage/coverage/index.html)
[![pre-commit.ci
status](https://results.pre-commit.ci/badge/github/seedcase-project/check-datapackage/main.svg)](https://results.pre-commit.ci/latest/github/seedcase-project/check-datapackage/main)
[![lifecycle](https://lifecycle.r-lib.org/articles/figures/lifecycle-experimental.svg)](https://lifecycle.r-lib.org/articles/stages.html#experimental)
[![Project Status: Active – The project has reached a stable, usable
state and is being actively
developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

`check-datapackage` is a Python package that checks your Data Package’s
metadata against the [Data Package standard](https://datapackage.org/)
to ensure that it’s compliant with the standard. Specifically, it:

- Checks your metadata in `datapackage.json` against the Data Package
  standard.
- Enables you to configure which components of the metadata should or
  should not be checked.
- Enables you to turn off specific checks defined in the standard.
- Supports user-defined, custom checks.
- Provides clear and user-friendly messages that point directly to where
  issues occur in the metadata.
- Supports a strict mode that enforces full compliance with the
  standard, including properties that must and should be included.

> [!WARNING]
>
> `check-datapackage` only checks the metadata in your
> `datapackage.json` file against the Data Package standard—it does not
> check the data itself against the metadata.

> [!TIP]
>
> This Python package was generated from the
> [`template-python-package`](https://github.com/seedcase-project/template-python-package)
> Seedcase template :tada:

## Project files and folders

- `.github/`: Contains GitHub-specific files, such as issue and pull
  request templates, workflows,
  [dependabot](https://docs.github.com/en/code-security/getting-started/dependabot-quickstart-guide)
  configuration, pull request templates, and a
  [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
  file.
- `tools/vulture-allowlist.py`: List of variables that shouldn’t be
  flagged by [Vulture](https://github.com/jendrikseipp/vulture) as
  unused.
- `tools/get-contributors.sh`: Script to get list of project
  contributors.
- `tests/`: Test files for the package.
- `src/`: Source code for the package.
- `docs/`: Documentation about using and developing the Python package.
- `_renderer.py`: Custom
  [`quartodoc`](https://machow.github.io/quartodoc/) renderer.
- `pytest.ini`: Pytest configuration file.
- `mypy.ini`: [`mypy`](https://mypy.readthedocs.io/en/stable/)
  configuration file for type checking Python code.
- `.copier-answers.yml`: Contains the answers you gave when copying the
  project from the template. **You should not modify this file
  directly.**
- `.cz.toml`:
  [Commitizen](https://commitizen-tools.github.io/commitizen/)
  configuration file for managing versions and changelogs.
- `.pre-commit-config.yaml`: [Pre-commit](https://pre-commit.com/)
  configuration file for managing and running checks before each commit.
- `.typos.toml`: [typos](https://github.com/crate-ci/typos) spell
  checker configuration file.
- `justfile`: [`just`](https://just.systems/man/en/) configuration file
  for scripting project tasks.
- `.editorconfig`: Editor configuration file for
  [EditorConfig](https://editorconfig.org/) to maintain consistent
  coding styles across different editors and IDEs.
- `CHANGELOG.md`: Changelog file for tracking changes in the project.
- `CITATION.cff`: Structured citation metadata for your project.
- `CONTRIBUTING.md`: Guidelines for contributing to the project.
- `_metadata.yml`: Quarto metadata file for the website, including
  information about the project, such as the titles and GitHub names.
- `pyproject.toml`: Main Python project configuration file defining
  metadata and dependencies.
- `_quarto.yml`: Quarto configuration file for the website, including
  settings for the website, such as the theme, navigation, and other
  options.
- `ruff.toml`: [Ruff](https://docs.astral.sh/ruff/) configuration file
  for linting and formatting Python code.
- `uv.lock`: Lockfile used by [`uv`](https://docs.astral.sh/uv/) to
  record exact versions of installed dependencies.

## Contributing

Check out our [contributing document](CONTRIBUTING.md) for information
on how to contribute to the project, including how to set up your
development environment.

Please note that this project is released with a [Contributor Code of
Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree
to abide by its terms.

### Contributors

The following people have contributed to this project by submitting pull
requests :tada:

[@lwjohnst86](https://github.com/lwjohnst86),
[@signekb](https://github.com/signekb),
[@martonvago](https://github.com/martonvago)

## Licensing

This project is licensed under the [MIT License](LICENSE.md).

## Changelog

For a list of changes, see our [changelog](CHANGELOG.md) page.

## Citing

This project is part of the [Seedcase
Project](https://seedcase-project.org), which is a collaborative effort
to create a framework for data management and analysis in research. If
you use this project in your work, please cite it as follows:

Johnston L.W., Brødbæk S.K., Beicher K., Vago M., Ostblom J. (2025).
Check Data Package: Ensure the correctness and compliance of your Data
Package DOI: 10.5281/zenodo.17733655 URL:
https://check-datapackage.seedcase-project.org

Or as a BibTeX entry:

    @misc{YourReferenceHere,
    author = {Johnston, Luke William and Brødbæk, Signe Kirk and Beicher, Kristiane and Vago, Marton and Ostblom, Joel},
    doi = {10.5281/zenodo.17733655},
    month = {11},
    title = {Check Data Package: Ensure the correctness and compliance of your Data Package},
    url = {https://check-datapackage.seedcase-project.org},
    year = {2025}
    }
