# Implementation Plan: Scientific Calculator

**Branch**: `001-scientific-calculator` | **Date**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-scientific-calculator/spec.md`

## Summary

Extend the existing calculator at `/` with scientific arithmetic, scientific functions and
constants, DEG/RAD trigonometry with an always-visible mode, non-destructive error recovery,
and bounded session history. The technical approach is one shared, registry-driven
calculation engine (`UI/calc_engine.py`) that both the Flask and FastAPI servers delegate to,
so every result, formatted display string, and domain error has a single owner
(Constitution Principles II, III, V, VII).

## Technical Context

**Language/Version**: Python 3.12 (standard library `math` and `ast` only)

**Primary Dependencies**: Flask, FastAPI, uvicorn, requests (already declared); `httpx` added
as a test-only dependency because `fastapi.testclient.TestClient` requires it

**Storage**: None server-side. Angle mode and history are session-only, in browser memory.

**Testing**: pytest for the engine and Flask routes; `fastapi.testclient.TestClient` for the
FastAPI port

**Target Platform**: Linux/WSL2 server; evergreen desktop browsers at 375, 768, and 1440 px

**Project Type**: Web application — one project, a static dependency-free frontend plus two
Python API servers sharing one domain layer

**Performance Goals**: Interactive latency only; no throughput target. Work is bounded by
`MAX_EXPRESSION_LENGTH` and `MAX_NESTING_DEPTH`.

**Constraints**: No build step; no numerical/symbolic libraries; no frontend framework or
chart library; no unrestricted `eval()`; both servers must agree semantically.

**Scale/Scope**: One calculator screen, five user stories, 26 functional requirements, and
roughly twenty additional operations.

## Design Decisions

**Single engine.** `UI/calc_engine.py` owns the exception hierarchy, constants, operation
registry, result formatter, and AST-based evaluator. `UI/app.py` (Flask) and
`UI/calculator.py` (FastAPI) become thin adapters: parse input, call the engine, render the
same success/error shape as today.

**Registry semantics.** `Operation(name, symbol, aliases, arity, impl, angle_aware, domain)`
plus an `OPERATIONS` mapping and `get_operation(name_or_symbol)`, which resolves aliases
case-insensitively. Adding a function is one registry entry plus tests.

**Evaluation result.** `evaluate(expression, angle_mode) -> EvaluationResult` with
`value: float`, `display: str`, `angle_mode: str`, and `is_trigonometric: bool`. The last
field is how the UI records angle mode in history without implementing any math or parsing
(FR-020, Constitution II).

**Angle mode.** Normalized once by `normalize_angle_mode` (`DEG`/`RAD`, default `DEG`,
anything else is `InvalidExpressionError`). Conversion happens only at `_to_radians` /
`_from_radians`; every internal trig computation uses radians (FR-012, FR-014, Principle VI).

**Formatting.** `format_result()` uses `SIGNIFICANT_DIGITS = 12`, strips unnecessary trailing
zeros, never emits `-0`, renders `0` for magnitudes below `ZERO_DISPLAY_THRESHOLD = 1e-12`,
and lets the 12-significant-digit formatter switch to scientific notation for very large or
very small values. Non-finite results raise `OverflowCalcError` (FR-015, Principle V).

**Constants.** `pi` and `e` resolve to `math.pi` / `math.e` at double precision and are
rendered by the same formatter (FR-009).

**Error policy.** `CalcError` (base, carries a user-facing `detail`) with
`InvalidExpressionError`, `DomainError`, and `OverflowCalcError`. All map to HTTP 400 with
human-readable messages and no internals (FR-016–FR-019, Principle V).

**Adjacency.** Implicit multiplication is rejected by the engine as
`InvalidExpressionError` (`2pi`, `π2`, `2 3`, `2sin(30)`); the frontend inserts an explicit
`*` where a user action would otherwise create an adjacent operand (FR-025).

**Bounding.** `MAX_EXPRESSION_LENGTH = 256` and `MAX_NESTING_DEPTH = 32`; `TAN_DOMAIN_EPSILON
= 1e-12` decides when `tan` is undefined (FR-017, Principle VII).

**Consolidation justification (Principles II and X).** Phase 2 of `tasks.md` deletes the
byte-for-byte duplicated `_safe_numeric`, `_evaluate_expression`, and `_apply_operation`
helpers from both servers. Principle X requires that this consolidation be its own,
explicitly specified change; this plan is that specification. It cannot be avoided: the new
scientific operations must live in a calculation layer, and Principle II forbids extending
the duplicated helpers. The API surface stays additive — `result` is retained and `display`,
`angle_mode`, and `is_trigonometric` are added.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Preserve Existing Functionality | PASS | `result`, both request shapes, every operator alias, `/`, and `/climate` are preserved; the 13-test baseline must not decrease. The error-UX refinement is required by FR-018/FR-019 and is recorded as a migration note in `CLAUDE.md` (T045). |
| II. Separation of UI and Calculation Logic | PASS (justified) | All new math goes to `calc_engine.py`; the Phase 2 consolidation is specified in §Design Decisions and §Complexity Tracking. |
| III. Scientific Calculator Extensibility | PASS | Registry entries plus `math` implementations; one entry and its tests per operation. |
| IV. Consistent Scientific UI | PASS | Constitution v2.0.1 names four categories (numbers, arithmetic operators, scientific functions, evaluation controls), matching FR-022. Grouping, `:focus-visible`, `aria-busy`, live region, reduced motion, contrast, and 375/768/1440 widths are covered by tasks. |
| V. Mathematical Correctness | PASS | One shared formatter, explicit domain errors, deterministic pure-Python math. |
| VI. Angle Mode Correctness | PASS | Explicit `angle_mode`, DEG default, single conversion boundary, both-mode tests. |
| VII. Safe Expression Evaluation | PASS | Extended character whitelist plus AST allowlist, arity checks, bounded length/depth, `__builtins__` disabled. |
| VIII. Test-Driven Changes | PASS | Per-operation matrix, both angle modes, both servers. |
| IX. Minimal Dependencies | PASS | Only `httpx` added, test-only, and declared in `UI/requirements.txt`. |
| X. Incremental Implementation | PASS | Eight phases; each leaves both servers runnable and the suite at or above 13 tests. |

> **Resolved (constitution v2.0.1, 2026-11-17):** Principle IV was amended from five
> categories to four — numbers, arithmetic operators, scientific functions, and evaluation
> controls — matching spec FR-022 and the exclusion of memory registers. No exception
> remains, and the Constitution Check passes in full.

## Project Structure

### Documentation (this feature)

```text
specs/001-scientific-calculator/
├── plan.md              # This file
├── spec.md              # Feature specification (needs no separate data model — §Key Entities)
├── tasks.md             # Task list; §Phase 2 holds the authoritative API contract
└── checklists/
    └── requirements.md
```

`research.md`, `data-model.md`, `quickstart.md`, and `contracts/` are intentionally not
separate files for this feature. The data model is the four entities in `spec.md` §Key
Entities; the API contract is recorded inline in `tasks.md` §Phase 2 and summarized in
§Design Decisions; the quickstart is the run commands already in `CLAUDE.md`.

### Source Code (repository root)

```text
UI/
├── calc_engine.py          # NEW: constants, exceptions, registry, formatter, evaluator
├── app.py                  # Flask adapter (local math removed)
├── calculator.py           # FastAPI adapter (local math removed; identical semantics)
├── climate.py              # unchanged
├── requirements.txt        # + httpx (test-only)
├── static/
│   ├── index.html          # grouped keypad, scientific group, angle-mode control, history
│   ├── script.js           # interaction state, API calls, history, skins
│   ├── style.css
│   ├── skins/{classic,modern}.css
│   └── climate.{html,css,js}  # unchanged
└── tests/
    ├── conftest.py
    ├── test_calc_engine.py # NEW domain tests
    ├── test_calc_api.py    # NEW Flask + FastAPI integration tests
    ├── test_climate.py     # unchanged
    └── test_static.py      # extended for history wiring
```

**Structure Decision**: Single project matching the existing repository. No new top-level
directories; the only new source modules are `UI/calc_engine.py` and the two test files.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Removing the duplicated `_safe_numeric` / `_evaluate_expression` / `_apply_operation` helpers from both servers (Principles II, X) | Scientific operations need exactly one implementation, and the duplication is what lets the two servers silently diverge. | Keeping the helpers and adding scientific math beside them creates a second engine, violates Principle II, and makes dual-server parity untestable. |
| New module `UI/calc_engine.py` | One owner for math, formatting, and errors, imported by both servers. | Putting the engine in `calculator.py` (which Principle II permits) would make the Flask app import the FastAPI application and break the script-launch model. |
