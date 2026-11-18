# Sensor-Monitor Constitution

## Core Principles

### I. Preserve Existing Functionality

The classical calculator MUST continue to work exactly as it does today while the
scientific calculator is added.

- Existing arithmetic operations, operator aliases (`+ add plus`, `- subtract minus`,
  `* x multiply`, `/ divide ÷`, `% mod modulo`, `** ^ power`), the expression form, and the
  `a`/`b`/`op` form MUST remain functional.
- Both `/api/calc` request paths and both server implementations MUST keep serving the
  calculator at `/`, and the Climate Trends tool MUST keep working.
- The existing test suite MUST pass unmodified; a test may change only when the change is
  the explicit subject of a specification, never to accommodate a regression.
- Behavior SHOULD be extended rather than replaced. Backward compatibility is required
  unless a specification explicitly declares a breaking change, and any such change MUST
  carry a migration note in `CLAUDE.md`.

**Rationale**: The application is a graded, working deliverable; an extension that breaks
the classical calculator is a failure even if the new feature works.

### II. Separation of UI and Calculation Logic

Mathematical logic MUST have a single owner and MUST NOT be duplicated across layers.

- `UI/calculator.py` and the shared calculation modules it uses own calculator operations
  and API logic.
- `UI/app.py` owns Flask application and UI integration (routing, static delivery, error
  rendering) and MUST delegate calculation to the calculation layer.
- Frontend JavaScript owns presentation and interaction state only. It MUST NOT implement
  arithmetic, scientific functions, angle conversion, or result formatting.
- New mathematical logic MUST be added to the calculation layer only. The existing
  duplicated helpers in `app.py` MUST NOT be extended or copied further; consolidating
  them is a separate, explicitly specified change.
- A change that alters a calculation's result MUST be made in one place, and both servers
  MUST exhibit the new behavior.

**Rationale**: Duplicated math is how the two servers silently disagree; a single engine
makes correctness testable and keeps the UI replaceable.

### III. Scientific Calculator Extensibility

Scientific functions MUST be modular and individually replaceable.

- Each operation MUST be a named, individually testable unit registered in an operation
  registry (name, symbol/alias, arity, implementation, domain-error behavior).
- Adding an operation SHOULD require only a registry entry plus its tests — no new route,
  no new frontend branch, no redesign.
- Python standard-library facilities (notably `math`) MUST be preferred over hand-rolled
  numerical code.
- Operations MUST declare their domain explicitly (for example real-domain only); an
  operation MUST NOT silently return a complex value when the application is in
  real-number mode.

**Rationale**: A registry-driven engine is what makes "add one function per increment"
cheap and keeps scientific coverage honest.

### IV. Consistent Scientific UI

The scientific calculator MUST preserve the familiar calculator workflow.

- Basic arithmetic MUST remain immediately accessible without navigating away or opening
  a panel.
- Scientific operations MUST be visually grouped separately from basic arithmetic.
- The interface MUST distinguish four categories: numbers, arithmetic operators,
  scientific functions, and evaluation controls.
- The layout MUST remain usable at common desktop browser sizes and at 375, 768, and
  1440 pixel widths.
- Controls MUST be keyboard operable with visible `:focus-visible` styling; async states
  MUST set `aria-busy` and disable controls; results and errors MUST be announced through a
  visually hidden live region; motion MUST respect `prefers-reduced-motion`; contrast MUST
  meet accessibility requirements.
- The frontend MUST remain static HTML/CSS/JS with no framework or chart library.

**Rationale**: Users of a calculator expect a stable muscle-memory layout; clustering
scientific keys without displacing the basic keypad preserves that while exposing depth.

### V. Mathematical Correctness

Scientific operations MUST be deterministic and mathematically correct.

- Domain errors MUST be handled explicitly and returned as controlled HTTP 400 responses
  with a human-readable `detail`: `sqrt` of a negative number in real mode, `log(0)` and
  other out-of-domain arguments, invalid expressions, and division by zero. A domain error
  MUST never surface as HTTP 500 or as a raw Python traceback.
- Floating-point output MUST be formatted by one shared formatter so that both servers and
  the UI display identical strings for identical results. The formatter MUST avoid
  locale-dependent output, negative zero, and spurious trailing digits.
- Numeric results MUST NOT depend on request order, process, or platform.
- A result that is mathematically undefined MUST be reported as an error, not coerced to
  a fabricated number.

**Rationale**: A scientific calculator is only useful if its errors match the mathematics
and its displayed digits are reproducible.

### VI. Angle Mode Correctness

Trigonometric operations MUST respect an explicit angle mode.

- The API and calculation layer MUST accept an explicit angle mode (`DEG` or `RAD`) for
  every trigonometric operation; no operation may infer or mix modes implicitly.
- The default mode MUST be explicitly defined and documented (DEG unless a specification
  states otherwise), and it MUST be applied identically by both servers.
- Conversion MUST happen at a single boundary; internal trigonometric computation MUST use
  radians.
- The currently selected mode MUST be visible in the UI at all times.
- Every trigonometric operation MUST be tested in both modes, including the degree/radian
  boundary values (0°, 30°, 45°, 90° and their radian equivalents).

**Rationale**: Silent degree/radian mixing produces plausible-looking wrong answers — the
worst failure mode for a scientific calculator.

### VII. Safe Expression Evaluation

User-provided expressions MUST NEVER be passed to unrestricted `eval()`.

- Evaluation MUST use the existing layered pattern: operator normalization, a character
  whitelist, `ast` parsing, and rejection of `Call`/`Attribute`/`Name`/subscript/collection
  nodes unless explicitly permitted.
- Scientific function calls MUST be admitted only through an allowlist that maps names to
  registered implementations and checks arity; unknown names and wrong arity MUST be
  rejected.
- Evaluation MUST run with `__builtins__` disabled.
- Expression length and nesting depth MUST be bounded to prevent resource exhaustion.
- Invalid or unsupported expressions MUST return a controlled HTTP 400 response; internal
  implementation details MUST NOT be echoed back.
- Extending the grammar MUST extend the whitelist and the AST/allowlist checks together;
  relaxing either alone is prohibited.

**Rationale**: Adding function calls to the grammar is exactly when an expression
evaluator becomes exploitable; the allowlist is the security boundary.

### VIII. Test-Driven Changes

Every newly introduced scientific operation MUST be tested, and the existing suite MUST
stay green.

- Tests live in `UI/tests/` and MUST pass with `python3 -m pytest UI/tests -q`.
- Each new operation MUST have tests covering: normal cases, boundary values, invalid
  inputs, and mathematical domain errors.
- Angle-aware operations MUST be tested in both modes; result formatting MUST have tests
  for its canonical cases.
- API integration changes MUST be tested through Flask's `app.test_client()` and, where
  the FastAPI port is affected, `fastapi.testclient`.
- Tests SHOULD be written before or alongside the implementation, and MUST be part of the
  same change.
- A change is not complete if it makes tests skipped, xfailed, or disabled.

**Rationale**: Scientific functions fail at their boundaries; a per-operation test matrix
is the only reliable guard.

### IX. Minimal Dependencies

The dependency surface MUST stay minimal.

- Python standard-library functionality MUST be preferred; `math` covers the required
  scientific functions unless a specification proves otherwise.
- numpy, scipy, pandas, and other numerical or symbolic libraries MUST NOT be added for
  this feature set without a recorded technical justification.
- New third-party dependencies MUST be justified in the change description and declared in
  `UI/requirements.txt`.
- The Flask-plus-FastAPI architecture MUST remain intact unless a specification explicitly
  requires an architectural change. Both servers MUST continue to share one calculation
  engine.
- The frontend MUST remain dependency-free; no CDN runtime or chart library.

**Rationale**: A small dependency set keeps the course project auditable, reproducible,
and offline-capable.

### X. Incremental Implementation

Scientific functionality MUST arrive in small, verifiable steps.

- Each step MUST leave the application in a working state: the full test suite passes and
  both servers start and serve the classical calculator.
- One operation (or one tightly coupled operation group) SHOULD be the unit of a step.
- Every step MUST be independently reviewable and revertible without breaking previously
  delivered steps.
- Unrelated refactoring, renaming, or cleanup MUST NOT be bundled with scientific-feature
  work. The `app.py`/`calculator.py` helper consolidation, if pursued, is its own
  specification.

**Rationale**: Incremental delivery keeps every commit demonstrable, which is what the
course milestones and the two-server design both depend on.

## Technology and Repository Constraints

- **Runtime**: Python 3.12 with Flask and FastAPI as the only web frameworks; `requests`
  for the Open-Meteo Archive API. Dependencies stay minimal and are declared in
  `UI/requirements.txt`.
- **Dual-server semantics**: Both server implementations MUST remain functional and MUST
  expose the same calculation semantics. Error shapes may differ (Flask returns
  `{"success": false, "detail": ...}`; FastAPI returns `{"detail": ...}`) but HTTP status
  semantics and the `detail` key MUST match. The retired byte-for-byte duplication rule is
  replaced by the single-engine rule in Principle II.
- **Launch model**: Servers are launched as scripts from the repository root
  (`python3 UI/app.py`, `python3 UI/calculator.py`), which places `UI/` on `sys.path`.
  `python3 -m UI.app` is unsupported.
- **Ports**: Flask owns 5000; FastAPI owns 8000. Port conflicts MUST be resolved by
  selecting the intended server, not by changing an implementation silently.
- **No build step**: There is no bundler, transpiler, or linter. Source files are the
  deployed artifacts.
- **Offline-first climate data**: Annual aggregates for every region MUST remain checked in
  under `UI/data/climate/`; tests MUST NOT touch the network; statistical computation MUST
  stay pure Python; data-quality constants (`MIN_VALID_DAYS`, `MIN_TREND_YEARS`, `ALPHA`)
  MUST remain explicit named constants.
- **Git as coursework artifact**: Branch layout (`main`, `development`, `staging`), history,
  and the existing stash are graded deliverables. History MUST NOT be rewritten, reset,
  rebased, or cleaned, and no commit, checkout, or stash operation MAY occur without an
  explicit user request.
- **Documentation of record**: Guidance for agents and contributors lives in `CLAUDE.md`;
  `README.md` is course metadata, not application documentation.

## Development Workflow and Quality Gates

1. **Specify before implementing**: Features follow the Spec Kit flow
   (`/speckit-specify` → plan → tasks) unless the change is a trivial fix.
2. **Baseline gate**: Before starting a scientific increment, record the current test
   result; the increment MUST NOT reduce it.
3. **Test gate**: `python3 -m pytest UI/tests -q` MUST pass, including the per-operation
   matrix from Principle VIII, before a change is complete.
4. **Dual-server gate**: The affected endpoint MUST be exercised on both servers, e.g.
   `curl -s 'http://localhost:5000/api/calc?expression=2+3*4'` and the port-8000
   equivalent, with identical semantic results.
5. **UI gate**: Frontend changes MUST be validated in a real browser per the
   `playwright-validation` skill, reviewed by `ui-reviewer`, and checked for keyboard
   operation, angle-mode visibility, category grouping, and the 375/768/1440 widths.
6. **Documentation gate**: Any change to endpoints, operators, angle-mode defaults,
   launch commands, or result formatting MUST update `CLAUDE.md` in the same change set.
7. **Review**: A reviewer MUST confirm gates 2–6 were executed, that no classical behavior
   regressed, and that the increment respected Principle X. Deviations require a recorded
   justification in the change description.

## Governance

- This constitution supersedes ad hoc practice. Where it conflicts with convenience, the
  constitution wins.
- **Amendments** MUST be proposed in writing, state the affected principles and version
  bump, and be reviewed before adoption. Each amendment MUST update the version line and
  dates below.
- **Versioning** follows semantic versioning: MAJOR for removal or incompatible redefinition
  of a principle; MINOR for a new principle or materially expanded guidance; PATCH for
  clarifications and non-semantic refinements.
- **Compliance review**: Every change MUST be checked against these principles. Complexity,
  duplicate implementations, and new dependencies MUST be justified against them.
- **Guidance**: Runtime development guidance for agents and contributors is maintained in
  `CLAUDE.md`; this constitution governs the rules that guidance must respect.
- Temporary review scaffolding for an amendment (such as a sync-impact report) MUST be removed
  before the amendment is committed.

**Version**: 2.0.1 | **Ratified**: 2026-11-17 | **Last Amended**: 2026-11-17
