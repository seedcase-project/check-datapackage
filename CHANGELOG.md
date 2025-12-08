# Changelog

Since we follow [Conventional
Commits](https://decisions.seedcase-project.org/why-conventional-commits),
we're able to automatically create a release with
[Commitizen](https://decisions.seedcase-project.org/why-semantic-release-with-commitizen)
based on the commit messages. This means that releases can happen quite
often, sometimes several in a day. It also means any individual release
will not have many changes within it. Below is a list of releases along
with what was changed within it.

## 0.24.0 (2025-12-08)

### Feat

- :sparkles: check primary key exists (#218)

## 0.23.1 (2025-11-27)

### Fix

- :bug: add dict check when getting parent instance (#214)

## 0.23.0 (2025-11-27)

### Feat

- :sparkles: `explain()` errors (#208)

## 0.22.2 (2025-11-21)

### Fix

- :bug: sort and deduplicate issues before raising error (#206)

## 0.22.1 (2025-11-20)

### Fix

- :bug: correct euro symbol representation (#207)

## 0.22.0 (2025-11-20)

### Feat

- :sparkles: support union operator in `RequiredCheck` (#201)

## 0.21.0 (2025-11-20)

### Feat

- :sparkles: disallow intersection JSON path operator (#203)

## 0.20.2 (2025-11-17)

### Refactor

- :recycle: fix name to `PropertyField` (not descriptor) (#194)

## 0.20.1 (2025-11-14)

### Refactor

- :recycle: rename to `properties` in `read_json()` (#169)

## 0.20.0 (2025-11-14)

### Feat

- ✨ handle grouped errors under the enum constraint (#183)

## 0.19.0 (2025-11-14)

### Feat

- :sparkles: handle grouped errors for primary key (#185)

## 0.18.0 (2025-11-13)

### Feat

- :sparkles: handle grouped foreign key errors (#188)

## 0.17.0 (2025-11-13)

### Feat

- :sparkles: expose `DataPackageError` (#192)

## 0.16.0 (2025-11-13)

### Feat

- ✨ handle grouped errors for licenses (#189)

## 0.15.0 (2025-11-13)

### Feat

- ✨ use Pydantic in config classes (#184)

## 0.14.0 (2025-11-05)

### Feat

- :sparkles: handle grouped errors under resource fields (#175)

## 0.13.0 (2025-11-04)

### Feat

- :sparkles: implement `error=True` in `check()` (#167)

## 0.12.1 (2025-11-04)

### Refactor

- :truck: rename to `extensions.py` from `custom_checks.py` (#158)

## 0.12.0 (2025-11-03)

### Feat

- :sparkles: adds `Extensions` meta-class (#165)

## 0.11.1 (2025-11-03)

### Refactor

- :recycle: handle grouped errors without modifying input (#177)

## 0.11.0 (2025-11-03)

### Feat

- :sparkles: add example field in resource (#174)

## 0.10.0 (2025-11-03)

### Feat

- :sparkles: exclude required issues at a given JSON path (#138)

## 0.9.0 (2025-10-29)

### Feat

- :sparkles: add `RequiredCheck` (#122)

## 0.8.7 (2025-10-21)

### Refactor

- ♻️ rename `check()` arg from `descriptor` to `properties` (#143)

## 0.8.6 (2025-10-21)

### Refactor

- 🚚 rename `Exclude` class to `Exclusion` (#145)

## 0.8.5 (2025-10-17)

### Refactor

- ♻️  rename example dicts from "descriptor" to "properties" (#140)

## 0.8.4 (2025-10-17)

### Refactor

- :recycle: simplify code to use `strict` mode (#127)

## 0.8.3 (2025-10-16)

### Refactor

- :truck: rename data package schema to include version (#135)

## 0.8.2 (2025-10-15)

### Fix

- :bug: filter out path and data errors correctly (#134)

## 0.8.1 (2025-10-15)

### Refactor

- 🚚 `Rule` to `CustomCheck` (#133)

## 0.8.0 (2025-10-14)

### Feat

- :sparkles: add exclusion by `jsonpath` (#85)

## 0.7.3 (2025-10-10)

### Refactor

- :fire: don't expose private constants (#113)

## 0.7.2 (2025-10-10)

### Refactor

- :fire: remove leftover code (#112)

## 0.7.1 (2025-10-09)

### Refactor

- :recycle: simplify handling of grouped errors (#81)

## 0.7.0 (2025-10-09)

### Feat

- :sparkles: implement rule logic (#108)

## 0.6.3 (2025-10-09)

### Refactor

- :recycle: move functionals to internals (#110)

## 0.6.2 (2025-10-07)

### Refactor

- :recycle: sort issues and remove duplicates at the very end (#109)

## 0.6.1 (2025-10-01)

### Refactor

- :truck: rename `target` and `location` to `jsonpath` (#89)

## 0.6.0 (2025-09-29)

### Feat

- :sparkles: add example descriptors (#83)

## 0.5.0 (2025-09-23)

### Feat

- :sparkles: exclude by JSON schema type in `check()` (#74)

## 0.4.0 (2025-09-23)

### Feat

- :sparkles: `read_json()` (#69)

## 0.3.1 (2025-09-23)

### Refactor

- :fire: remove unused code after redesign (#77)

## 0.3.0 (2025-09-22)

### Feat

- :sparkles: add `Issue` class (#67)

## 0.2.1 (2025-09-19)

### Refactor

- :recycle: start aligning `check()` with design (#60)

## 0.2.0 (2025-09-18)

### Feat

- :sparkles: add `Config`, `Rule`, `Exclude` (#59)

## 0.1.1 (2025-09-16)

### Fix

- :bug: fix website build (#27)
