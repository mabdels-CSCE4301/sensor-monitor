---

description: "Task list for the Scientific Calculator feature"
---

# Tasks: Scientific Calculator

**Input**: Design documents from `/specs/001-scientific-calculator/`

**Prerequisites**: `spec.md` (user stories P1–P5), `.specify/memory/constitution.md` v2.0.1

**Note**: `plan.md` records the technical design and the Constitution Check (all principles pass). The authoritative `/api/calc` contract lives in §Phase 2 below. `data-model.md`, `research.md`, `quickstart.md`, and `contracts/` are intentionally consolidated into `spec.md`, `plan.md`, and this file (see plan.md §Documentation).

**Tests**: Included. The specification does not request TDD, but Constitution Principle VIII ("Test-Driven Changes") mandates tests for every new operation, both angle modes, formatting, and API integration on both servers.

**Organization**: Tasks are grouped by user story so each story is an independently implementable and testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Path Conventions

This is a single-project Flask + FastAPI application. All code lives under `UI/`, static assets under `UI/static/`, and tests under `UI/tests/`.

**Terminology**: "existing calculator" means the pre-feature calculator behavior (what the constitution calls the "classical calculator"). It is not the `classic` UI skin; the skins are unaffected by this feature.

```text
UI/
├── calc_engine.py          # NEW shared calculation engine (single owner of math)
├── app.py                  # Flask server (delegates to calc_engine)
├── calculator.py           # FastAPI server (delegates to calc_engine)
├── requirements.txt
├── static/
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── skins/{classic,modern}.css
└── tests/
    ├── conftest.py
    ├── test_calc_engine.py # NEW domain/unit tests
    ├── test_calc_api.py    # NEW Flask + FastAPI integration tests
    ├── test_climate.py
    └── test_static.py
```

**Baseline recorded at task-generation time**: `python3 -m pytest UI/tests -q` → **13 passed**. This count MUST NOT decrease (Constitution gate 2).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the engine module, the shared error/constant vocabulary, and the test scaffolding every story depends on.

- [X] T001 Record the baseline by running `python3 -m pytest UI/tests -q` from the repository root and confirming 13 passed before any change; note any deviation in the change description (Constitution gate 2)
- [X] T002 Create `UI/calc_engine.py` with the shared exception hierarchy — `CalcError` (base, carries a user-facing `detail`), `InvalidExpressionError(CalcError)`, `DomainError(CalcError)`, `OverflowCalcError(CalcError)` — and named constants with pinned values: `DEFAULT_ANGLE_MODE = "DEG"`, `ANGLE_MODES = ("DEG", "RAD")`, `MAX_EXPRESSION_LENGTH = 256`, `MAX_NESTING_DEPTH = 32`, `SIGNIFICANT_DIGITS = 12`, `ZERO_DISPLAY_THRESHOLD = 1e-12`, `TAN_DOMAIN_EPSILON = 1e-12`
- [X] T003 [P] Create `UI/tests/test_calc_engine.py` with a module-level docstring and imports of `calc_engine`, plus `UI/tests/test_calc_api.py` with imports of `app` (Flask) and `calculator` (FastAPI); no assertions yet, so the suite still passes
- [X] T004 [P] Add `httpx` to `UI/requirements.txt` with a comment that `fastapi.testclient.TestClient` requires it, satisfying the declaration rule in Constitution Principle IX

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the single calculation engine and rewire both servers onto it. Every user story depends on this phase because every story evaluates through `/api/calc`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

**API contract established here** (no `contracts/` file exists; this is the authoritative shape):

- Request: `GET`/`POST /api/calc` accepts `expression`, or `a`/`b`/`op`, plus optional `angle_mode` (`DEG` or `RAD`, default `DEG`).
- Success body: `{"success": true, "result": <float>, "display": "<formatted string>", "expression": "...", "angle_mode": "DEG", "is_trigonometric": false}` for expression mode; the `a`/`b`/`op` form keeps its existing keys and adds `display`, `angle_mode`, and `is_trigonometric` (always `false`).
- Error: HTTP 400. Flask body `{"success": false, "detail": "..."}`; FastAPI body `{"detail": "..."}`. `result` stays numeric for backward compatibility; the UI renders `display`.

- [X] T005 Implement `format_result(value: float) -> str` in `UI/calc_engine.py`: up to 12 significant digits (`SIGNIFICANT_DIGITS`), strip unnecessary trailing zeros, never emit `"-0"`, collapse magnitudes below `ZERO_DISPLAY_THRESHOLD` to `"0"`, use scientific notation for very large/small magnitudes, and raise `OverflowCalcError` for non-finite or overflowing values
- [X] T006 Implement the operation registry in `UI/calc_engine.py`: an `Operation` dataclass with `name`, `symbol`, `aliases`, `arity`, `impl`, `angle_aware` (bool), and `domain` metadata; an `OPERATIONS` mapping; and `get_operation(name_or_symbol)` that resolves aliases case-insensitively. Do not define scientific operations yet — they arrive per story
- [X] T007 Implement `apply_operation(left: float, right: float, operator: str) -> float` in `UI/calc_engine.py`, preserving every existing alias (`+ add plus`, `- subtract minus`, `* x multiply`, `/ divide ÷`, `% mod modulo`, `** ^ power`) and the existing division-by-zero rule
- [X] T008 Implement the safe evaluator in `UI/calc_engine.py`: normalize `×`→`*`, `÷`→`/`, `^`→`**`; enforce a character whitelist that admits digits, `.`, whitespace, `+ - * / % ( )`, and the ASCII letters needed for registered function names and the constants `pi`/`e`, extending the whitelist and the AST allowlist together (Constitution VII); enforce `MAX_EXPRESSION_LENGTH`; reject implicit multiplication (adjacent operands such as `2pi`, `π2`, `2 3`, or `2sin(30)`) as `InvalidExpressionError`; parse with `ast`; reject `Attribute`, `Subscript`, `List`, `Tuple`, `Dict`, `Set`, comprehensions, and keyword/star arguments; allow `ast.Name` only for the constants `pi` and `e`; allow `ast.Call` only for names in the registry with the declared arity; enforce `MAX_NESTING_DEPTH`; evaluate with `{"__builtins__": {}}`; translate `SyntaxError`, `ZeroDivisionError`, and domain failures into the `CalcError` subclasses with non-technical messages
- [X] T009 Implement angle-mode plumbing in `UI/calc_engine.py`: `normalize_angle_mode(value) -> str` (case-insensitive `DEG`/`RAD`, default `DEFAULT_ANGLE_MODE`, raise `InvalidExpressionError` for anything else) and a single conversion boundary `_to_radians`/`_from_radians` that internal trigonometry uses
- [X] T010 Implement `evaluate(expression: str, angle_mode: str = DEFAULT_ANGLE_MODE) -> EvaluationResult` in `UI/calc_engine.py`, composing T008 + T006 + T005 and returning an `EvaluationResult` dataclass with `value: float`, `display: str`, `angle_mode: str`, and `is_trigonometric: bool` (set when any angle-aware operation ran)
- [X] T011 [P] Rewire `UI/app.py`: delete the local `_safe_numeric`, `_evaluate_expression`, and `_apply_operation` math; import `calc_engine`; parse `angle_mode` from query/JSON; return `result`, `display`, `expression`, `angle_mode`, and `is_trigonometric`; map `calc_engine.CalcError` to HTTP 400 with the existing `{"success": false, "detail": ...}` shape
- [X] T012 [P] Rewire `UI/calculator.py` identically to T011 using the FastAPI `HTTPException(status_code=400, detail=...)` shape; keep the `a`/`b`/`op` path and both GET/POST methods working, and return the same five success keys
- [X] T013 [P] Add foundational unit tests to `UI/tests/test_calc_engine.py`: formatter canonical cases (12 digits, trailing zeros, negative zero, scientific notation, zero threshold, overflow), alias resolution, division by zero, `EvaluationResult` fields (including `is_trigonometric`), and evaluator safety (rejects `__import__`, attribute access, unknown names, wrong arity, implicit multiplication, over-length and over-nested input; absolute value works with builtins disabled)
- [X] T014 [P] Add API integration tests to `UI/tests/test_calc_api.py`: exercise `/api/calc` through Flask `app.test_client()` and FastAPI `fastapi.testclient.TestClient`, asserting identical semantics, the `display` and `is_trigonometric` keys, `angle_mode` echo, 400 status, and each server's error body shape

**Checkpoint**: Both servers run all arithmetic through one engine; the suite is green.

---

## Phase 3: User Story 1 — Evaluate arithmetic expressions (Priority: P1) 🎯 MVP

**Goal**: Build and evaluate arithmetic expressions with standard precedence, unary minus, decimals, and parentheses; keep the expression and result visible as separate areas.

**Independent Test**: Enter each acceptance example by mouse and keyboard — `2 + 3 × 4 = 14`, `(2 + 3) × 4 = 20`, `-5 + 2 = -3` — then press Delete and Clear on a partial expression and confirm the expected edits.

### Tests for User Story 1

- [X] T015 [P] [US1] Add arithmetic tests to `UI/tests/test_calc_engine.py`: precedence (`2+3*4`→14), parentheses (`(2+3)*4`→20), unary minus (`-5+2`→-3), decimals, right-associative exponentiation (`2^3^2`→512), and unary-minus precedence (`-2^2`→-4)
- [X] T016 [P] [US1] Add API tests to `UI/tests/test_calc_api.py` covering the three acceptance examples through both Flask and FastAPI, asserting `display` strings match

### Implementation for User Story 1

- [X] T017 [US1] Register basic arithmetic and power operations in `OPERATIONS` in `UI/calc_engine.py` (`+`, `-`, `*`, `/`, `%`, `**`, plus `square` for `x²` and `power` for `xʸ`), with correct exponent associativity and unary-minus precedence
- [X] T018 [US1] Restructure `UI/static/index.html`: keep `#expression` and `#display` as separate areas, and wrap the keypad in labeled groups (`<div class="key-group" role="group" aria-label="Numbers">`, `...="Arithmetic">`, `...="Evaluation">`) without changing existing `data-value` attributes, so `script.js` and current tests keep working
- [X] T019 [US1] Add a sign-change key (`data-value="±"`, `aria-label="Change sign"`) and an `x²` key to `UI/static/index.html` in the arithmetic/function group
- [X] T020 [US1] Update `UI/static/script.js` for US1: handle `±` (toggle the sign of the current operand inside the expression), handle `x²` by appending `^2`, render `data.display` instead of `String(data.result)`, and keep the evaluated expression visible after `=`
- [X] T021 [US1] Style the grouped keypad, `±`, and `x²` in `UI/static/style.css` while preserving the existing four-column grid, `:focus-visible`, `:disabled`, and `prefers-reduced-motion` rules

**Checkpoint**: MVP — arithmetic expressions evaluate correctly from mouse and keyboard, and the classical keypad still works.

---

## Phase 4: User Story 2 — Recover safely from invalid input (Priority: P2)

**Goal**: Show clear, non-technical errors for division by zero, out-of-domain arguments, and malformed expressions, while keeping the expression editable and the calculator operational.

**Independent Test**: Submit `5 / 0`, `2 +`, and `(2+3`; each shows a specific message, the expression stays editable, and a correction then evaluates successfully.

### Tests for User Story 2

- [X] T022 [P] [US2] Add error-taxonomy tests to `UI/tests/test_calc_engine.py`: `5/0` → division-by-zero `CalcError`; `2+`, `(2+3`, and empty input → `InvalidExpressionError`; adjacent operands (`2pi`, `2 sin(30)`) → `InvalidExpressionError`; overflow (`2^100000`) → `OverflowCalcError`; every message is human-readable and contains no Python exception class names
- [X] T023 [P] [US2] Add API error tests to `UI/tests/test_calc_api.py` for both servers: HTTP 400, correct body shape, and `detail` present, never HTTP 500

### Implementation for User Story 2

- [X] T024 [US2] Harden error translation in `UI/calc_engine.py`: catch `ZeroDivisionError`, `OverflowError`, and `math` domain errors at the registry boundary and re-raise the matching `CalcError` subclass; ensure `detail` strings are user-facing and leak no internals
- [X] T025 [US2] Update `UI/static/script.js` error handling to meet FR-019: on failure, keep `state.expression` editable (do not overwrite it with `'invalid'`), display the server `detail` in the result area, set `.is-error`, announce it through `#calc-status`, remove the destructive 800 ms auto-clear, and clear `state.isError` in the input handlers (`inputDigit`, `inputDecimal`, `inputOperator`, `deleteLast`) so the first corrective keystroke edits the retained expression instead of being ignored
- [X] T026 [US2] Update `UI/static/style.css` so the error state (`.is-error`, error text) is visible with sufficient contrast and does not shift layout

**Checkpoint**: Every listed error is recoverable; no evaluation can leave the UI stuck.

---

## Phase 5: User Story 3 — Use scientific functions and constants (Priority: P3)

**Goal**: Provide square root, `x²`, `xʸ`, `eˣ`, `ln`, `log`, `abs`, and insertable `π` and `e`, nestable and usable anywhere a number is allowed.

**Independent Test**: Evaluate `sqrt(16)=4`, `2^8=256`, `x²` on 7 `=49`, `ln(e)=1`, `log(1000)=3`, `abs(-7)=7`, and insert π and confirm its displayed precision.

### Tests for User Story 3

- [X] T027 [P] [US3] Add per-function tests to `UI/tests/test_calc_engine.py`: normal cases for `sqrt`, `square`, `power`, `exp`, `ln`, `log`, `abs`; constants `pi`/`e`; nesting (`sqrt(abs(-16))`→4); and domain errors (`sqrt(-1)`, `ln(0)`, `ln(-5)`, `log(0)`, `log(-5)`)
- [X] T028 [P] [US3] Add API tests to `UI/tests/test_calc_api.py` for one representative expression per function and for the constants, through both servers

### Implementation for User Story 3

- [X] T029 [US3] Register scientific operations in `OPERATIONS` in `UI/calc_engine.py` using the Python `math` module (`sqrt`, `square`, `power`, `exp`, `ln`→`math.log`, `log`→`math.log10`, `abs`), with explicit real-domain checks and `DomainError` for negative `sqrt`, non-positive logs, and non-finite `exp` results
- [X] T030 [US3] Add `pi` and `e` to the constants allowlist in `UI/calc_engine.py` so `ast.Name` nodes resolve to `math.pi`/`math.e` and nest inside any expression
- [X] T031 [US3] Add the scientific key group to `UI/static/index.html` (`sqrt(`, `xʸ`, `eˣ`, `ln(`, `log(`, `abs(`, `π`, `e`) inside a `<div class="key-group scientific" role="group" aria-label="Scientific functions">` that is visually separate from arithmetic, plus a trigonometric group (`sin(`, `cos(`, `tan(`, `asin(`, `acos(`, `atan(`) for FR-011. Do not add a second `x²` key — the single `x²` control comes from T019; adding two buttons with `data-value="x²"` would also break the keyboard lookup that resolves the first match
- [X] T032 [US3] Update `UI/static/script.js` to insert scientific tokens: function keys insert `name(` and auto-close the matching `)` when the expression ends with an operand, `π` inserts `pi`, `e` inserts `e`, and `xʸ` inserts `^`; when an insertion would follow an operand or `)`, insert an explicit `*` first (so `2` + π becomes `2*pi` and `2` + `sin(` becomes `2*sin(`) so adjacent operands are never produced (FR-025); keep keyboard handling working when a scientific key has focus
- [X] T033 [US3] Style the scientific group in `UI/static/style.css` and adjust the scoped selectors in `UI/static/skins/classic.css` and `UI/static/skins/modern.css` if the new group needs skin-specific treatment; keep every skin selector under `html[data-skin="<name>"]`

**Checkpoint**: All scientific functions and constants work by mouse and keyboard, with nesting.

---

## Phase 6: User Story 4 — Trigonometry with a visible angle mode (Priority: P4)

**Goal**: Provide sin/cos/tan and inverses, always show the active DEG/RAD mode, default to DEG, and apply one explicitly selected mode to every trig evaluation.

**Independent Test**: Evaluate `sin(30)` in DEG (`0.5`) and `sin(π/2)` in RAD (`1`), switch modes between evaluations, and confirm `asin(0.5)` returns `30` in DEG; the mode indicator updates immediately and stays visible.

### Tests for User Story 4

- [X] T034 [P] [US4] Add trig tests to `UI/tests/test_calc_engine.py`: `sin(30)` DEG→0.5, `sin(pi/2)` RAD→1, `cos(60)` DEG→0.5, `tan(45)` DEG→1, `asin(0.5)` DEG→30, `acos(0.5)` DEG→60, `atan(1)` DEG→45, boundary values at 0/30/45/90 degrees and radian equivalents, `tan(90)` DEG→`DomainError`, `asin(2)`/`acos(-2)`→`DomainError`, and invalid angle modes→`InvalidExpressionError`
- [X] T035 [P] [US4] Add API tests to `UI/tests/test_calc_api.py`: `angle_mode` accepted on both servers, default DEG when omitted, RAD honored, the value echoed in the success body, and `is_trigonometric` true for trig expressions and false otherwise

### Implementation for User Story 4

- [X] T036 [US4] Register angle-aware trig operations in `OPERATIONS` in `UI/calc_engine.py` (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`) with `angle_aware=True`; internal computation uses radians via the T009 boundary; `tan` raises `DomainError` when `abs(cos(radians)) < TAN_DOMAIN_EPSILON`; inverse results convert back to the active mode
- [X] T037 [US4] Thread `angle_mode` through `evaluate()` in `UI/calc_engine.py` so every trig call receives exactly one normalized mode and no operation infers or mixes modes
- [X] T038 [US4] Add a DEG/RAD toggle and an always-visible mode indicator to `UI/static/index.html` (radio group or segmented buttons with `aria-pressed`, plus a persistent label such as `#angle-mode-indicator` readable without interaction)
- [X] T039 [US4] Update `UI/static/script.js` to keep the selected mode in session state with DEG as the default, send it as `angle_mode` on every `/api/calc` request, update the indicator immediately on change, and include the evaluated mode in the status announcement
- [X] T040 [US4] Style the angle-mode control and indicator in `UI/static/style.css`, including `:focus-visible`, contrast, and narrow-width behavior at 375 px

**Checkpoint**: Trigonometry is correct in both modes, and the active mode is always visible.

---

## Phase 7: User Story 5 — Review calculation history (Priority: P5)

**Goal**: Record every successful evaluation as `expression = result` plus its angle mode when trigonometric, newest first, capped at the 50 most recent entries for the session; exclude failures.

**Independent Test**: Evaluate three expressions, confirm all three appear newest first; evaluate a trig expression and confirm its mode is recorded; trigger a failed evaluation and confirm it is absent.

### Tests for User Story 5

- [X] T041 [P] [US5] Extend `UI/tests/test_static.py` with assertions that `/` serves a history container (e.g. `id="history"`), a history list, and a clear-history control, so the wiring is covered without a browser

### Implementation for User Story 5

- [X] T042 [US5] Add the history markup to `UI/static/index.html`: a `<section id="history" aria-label="Calculation history">` with a heading, a `<ol id="history-list">`, an empty-state message, and a clear-history button
- [X] T043 [US5] Implement session history in `UI/static/script.js`: append `{expression, display, angle_mode}` only after a successful response, ignore failures, keep at most 50 entries (`HISTORY_LIMIT`), render newest first as `expression = display`, show the angle mode for entries whose response had `is_trigonometric === true` (never infer trig from the expression text), and clear the list on demand
- [X] T044 [US5] Style the history panel responsively in `UI/static/style.css` (stacked below the calculator at 375 px, alongside it at wider widths) with accessible contrast and no horizontal scroll

**Checkpoint**: History is correct, bounded, session-only, and failure-free.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, dual-server verification, browser validation, review, and regression proof across all stories.

- [X] T045 [P] Update `CLAUDE.md` (Documentation gate) to document `UI/calc_engine.py`, the operation registry, the `angle_mode` request parameter and its DEG default, the new `display` and `is_trigonometric` response fields, the scientific/trig key groups, session history behavior, and the error-UX migration note required by Constitution Principle I (the 800 ms auto-clear and `invalid` substitution are replaced by an editable expression with a persistent `detail` message)
- [X] T046 Run the full suite `python3 -m pytest UI/tests -q` and confirm every test passes with no skips or xfails (Constitution gates 2 and 3)
- [X] T047 Verify dual-server parity (Constitution gate 4): start `python3 UI/app.py` and `python3 UI/calculator.py`, then compare equivalent `curl` calls on ports 5000 and 8000 for `2+3*4`, `sqrt(16)`, `sin(30)&angle_mode=DEG`, `sin(pi/2)&angle_mode=RAD`, `5/0`, and the `a`/`b`/`op` aliases; results and statuses must match semantically
- [X] T048 Confirm the classical calculator is unchanged in `UI/static/script.js`, `UI/static/index.html`, `UI/app.py`, and `UI/calculator.py`: `7 × 8 = 56`, division-by-zero error and recovery, chaining, keyboard input, skin switching, the `/climate` page, and existing operator aliases (Constitution Principle I)
- [X] T049 Run real-browser validation against `UI/static/index.html` per `../.claude/skills/playwright-validation/SKILL.md` at 375, 768, and 1440 px: arithmetic by mouse and keyboard, every error case and recovery, scientific functions, both angle modes, history ordering and cap, `:focus-visible`, `aria-busy`, live-region announcements, and `prefers-reduced-motion`; also confirm a 15-entry expression can be entered and evaluated in under 30 seconds using the mouse alone and again with the keyboard alone (SC-004), and that a second decimal point in one number is still prevented (spec edge case)
- [X] T050 Run the `ui-reviewer` agent on the changes under `UI/static/` and both backends; address report-only findings that indicate gate failures (the agent must not edit code or touch Git)
- [X] T051 [P] Confirm `UI/requirements.txt` declares only `fastapi`, `uvicorn`, `flask`, `requests`, `pytest`, and `httpx`, with `httpx` justified for `TestClient`, and that no numerical library (numpy/scipy/pandas) was added (Constitution Principle IX)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**.
- **User Stories (Phases 3–7)**: All depend on Phase 2. In practice, deliver them sequentially in priority order because they share `calc_engine.py`, `index.html`, `script.js`, and `style.css`. US2–US5 can be developed in parallel only with careful file coordination.
- **Polish (Phase 8)**: Depends on all delivered stories.

### User Story Dependencies

- **US1 (P1)**: Only Phase 2 dependency. Delivers the MVP.
- **US2 (P2)**: Depends on US1's keypad/error surface but is independently testable with malformed input.
- **US3 (P3)**: Depends on Phase 2 registry and US1's keypad structure.
- **US4 (P4)**: Depends on US3's function-registry pattern and US1's UI groups; independent of US2.
- **US5 (P5)**: Depends on US1–US4 only in that it records their successful results; the history state itself is independent.

### Within Each User Story

- Tests first (or alongside), and they must fail before implementation.
- Engine operations in `UI/calc_engine.py` before server/UI wiring.
- Markup in `index.html` before behavior in `script.js`, before styling.
- Complete the story's checkpoint before starting the next priority.

### Parallel Opportunities

- **Phase 1**: T003 and T004 are `[P]` (different files).
- **Phase 2**: T005–T010 all edit `UI/calc_engine.py` and are sequential; T011 and T012 are `[P]` (different servers) once T007–T010 exist; T013 and T014 are `[P]` (different test files).
- **Phase 3**: T015 and T016 are `[P]`; T017 can precede UI work.
- **Phase 4**: T022 and T023 are `[P]`.
- **Phase 5**: T027 and T028 are `[P]`.
- **Phase 6**: T034 and T035 are `[P]`.
- **Phase 7**: T041 is `[P]` against earlier static work.
- **Phase 8**: T045 and T051 are `[P]`.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# The engine tasks share one file and must run in order:
Task: "Implement format_result in UI/calc_engine.py"                 # T005
Task: "Implement the Operation registry in UI/calc_engine.py"         # T006 — same file: sequence, don't truly parallelize

# Once the engine is in place, rewire each server independently:
Task: "Rewire UI/app.py /api/calc onto calc_engine"                  # T011
Task: "Rewire UI/calculator.py /api/calc onto calc_engine"           # T012

# Then write the two test suites together:
Task: "Foundational unit tests in UI/tests/test_calc_engine.py"      # T013
Task: "API integration tests in UI/tests/test_calc_api.py"           # T014
```

> **Note**: T005 and T006 both edit `UI/calc_engine.py`, so treat them as sequential in a single-editor workflow; the `[P]` marks in Phase 2 only hold where files differ.

---

## Parallel Example: User Story 4

```bash
# Tests for both modes can be written together:
Task: "Trig tests in UI/tests/test_calc_engine.py"                   # T034
Task: "angle_mode API tests in UI/tests/test_calc_api.py"            # T035
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational — one `calc_engine.py`, both servers rewired, 13 existing tests still green.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `python3 -m pytest UI/tests -q`; exercise `2+3*4`, `(2+3)*4`, `-5+2` by mouse and keyboard; confirm `7×8=56` and `/climate` still work.
5. Deploy/demo the arithmetic MVP.

### Incremental Delivery

1. Setup + Foundational → one engine, dual-server parity.
2. US1 → arithmetic + sign change + `x²` (MVP).
3. US2 → error taxonomy and non-destructive recovery.
4. US3 → scientific functions and constants.
5. US4 → trigonometry with a visible DEG/RAD mode.
6. US5 → bounded session history.
7. Polish → docs, dual-server smoke tests, browser validation, reviewer pass.

Each increment must leave both servers runnable and the test count at or above 13 (Constitution Principle X).

### Parallel Team Strategy

With multiple contributors, complete Setup + Foundational together, then assign:

- Contributor A: US1 → US2 (interaction and error surface).
- Contributor B: US3 → US4 (engine operations and angle mode).
- Contributor C: US5 (history UI), then Polish validation.

Stories share `script.js` and `index.html`; coordinate edits per file and merge engine changes through `calc_engine.py` only.

---

## Notes

- `[P]` means different files and no unfinished dependency; it does not override same-file ordering.
- All new math belongs in `UI/calc_engine.py` only. Do not extend or copy the old helpers in `UI/app.py` or `UI/calculator.py` (Constitution Principle II).
- Never pass user input to unrestricted `eval()`; the AST allowlist is the security boundary (Principle VII).
- Every new operation gets normal, boundary, invalid, and domain-error tests in both angle modes where applicable (Principle VIII).
- No new dependencies beyond `httpx` for tests (Principle IX).
- Do not commit, branch, check out, or stash — Git history is a graded artifact and requires an explicit user request.
