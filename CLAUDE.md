# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Course project for "AI-Assisted Software Development with VS Code, Git, Claude & GitHub Spec Kit". The application is a **scientific calculator** (`/`) plus a **Climate Trends explorer** (`/climate`): a Flask server (`UI/app.py`, primary) or a FastAPI port (`UI/calculator.py`) exposing arithmetic and climate APIs, plus dependency-free HTML/CSS/JS frontends. `README.md` is course metadata (date, author, milestones), not app documentation. The repository's Git history, branches, and stash are themselves coursework artifacts — treat them as read-only (see Git).

Despite the directory name, there is no sensor-monitoring code. The climate feature analyses ERA5 reanalysis, not live sensors.

Claude Code tooling for this project lives one directory above the repository, in `../.claude/` (see Claude tooling).

## Commands

Run from the repository root (`sensor-monitor/`). There is no build step, linter, or checked-in virtualenv; dependencies in `UI/requirements.txt` are unpinned.

```bash
pip install -r UI/requirements.txt

python3 UI/app.py            # Flask calculator + climate → http://localhost:5000 (debug reloader)
python3 UI/calculator.py     # FastAPI variant         → http://localhost:8000 (uvicorn reload)
python3 UI/sample.py         # alias that imports the Flask app, also port 5000

python3 -m pytest UI/tests -q
python3 -m pytest UI/tests/test_static.py::test_modern_skin_is_served_and_scoped -q   # one test
python3 -m pytest UI/tests/test_climate.py -q                                        # climate tools
```

Launch the servers as scripts, not modules. Both import the domain layer with `from climate import ...`, which only resolves because running `UI/app.py` puts `UI/` at the front of `sys.path`; `python3 -m UI.app` fails.

Flask (5000) and FastAPI (8000) can run concurrently; `app.py` and `sample.py` both bind 5000, so those two conflict. Both serve `UI/static/` under `/static/...` on the same origin as `/api/...`, so the frontends need no CORS setup.

Smoke-test the APIs without a browser (use port 8000 with the FastAPI server):

```bash
curl -s 'http://localhost:5000/api/calc?expression=2+3*4'
curl -s 'http://localhost:5000/api/calc?a=7&b=8&op=multiply'
curl -s 'http://localhost:5000/api/calc?expression=sin(30)&angle_mode=DEG'
curl -s 'http://localhost:5000/api/climate/options'
curl -s 'http://localhost:5000/api/climate/trend?region=london&measure=temperature'
```

## Architecture

### One API, two server implementations

`/api/calc` (GET or POST; query params or JSON body) accepts either:

- `expression` — an expression such as `"2+3*4"` or `"sqrt(16)+sin(30)"`, or
- `a`, `b`, `op` — two numbers and an operator,

plus an optional `angle_mode` (`DEG` or `RAD`; default `DEG`).

Success bodies include `result` (numeric, unchanged for compatibility), `display` (the formatted string the UI renders), `angle_mode`, and `is_trigonometric` (true when any angle-aware operation ran). Flask errors return HTTP 400 with `{"success": false, "detail": "..."}`; FastAPI 400s use `{"detail": "..."}` via `HTTPException` (no `success` field). The frontend keys off the HTTP status and `detail`, so both work. New endpoints generally need adding to both servers.

`op` accepts symbols and aliases: `+ add plus`, `- subtract minus`, `* x multiply`, `/ divide ÷`, `% mod modulo`, `** ^ pow xʸ power`. Scientific names are `sqrt`, `square`, `exp`, `ln`, `log`, `abs`, and `sin cos tan asin acos atan`.

### Calculation engine

`UI/calc_engine.py` is the single owner of arithmetic, scientific operations, angle handling, result formatting, and calculation errors. Both servers are thin adapters: they parse input, call `calc_engine.evaluate(...)` or `calc_engine.apply_operation(...)`, and render the same success/error shapes.

- Operations live in an `OPERATIONS` registry (`Operation(name, symbol, aliases, arity, impl, angle_aware, domain)`); `get_operation()` resolves names, symbols, and aliases case-insensitively. Add a function by registering one entry plus tests — no route and no frontend branch.
- `evaluate(expression, angle_mode)` returns `EvaluationResult(value, display, angle_mode, is_trigonometric)`.
- `format_result()` uses 12 significant digits, strips trailing zeros, collapses magnitudes below `ZERO_DISPLAY_THRESHOLD` to `0`, never emits `-0`, and raises `OverflowCalcError` for non-finite values.
- The exception hierarchy is `CalcError` → `InvalidExpressionError`, `DomainError`, `OverflowCalcError`; each carries a user-facing `detail` and maps to HTTP 400.
- Angle conversion happens only at `_to_radians` / `_from_radians`; trig internals always use radians. `DEFAULT_ANGLE_MODE` is `DEG`.

Do not add calculator math to `app.py` or `calculator.py`; the previous byte-for-byte helper duplication was retired in favour of the engine.

### Expression safety

The engine normalizes unicode operators (`×`, `÷`, `−`, `π`, `^`), enforces `MAX_EXPRESSION_LENGTH`, applies a character whitelist that admits letters only because registered function names and the constants `pi`/`e` need them, enforces `MAX_NESTING_DEPTH` (parenthesis depth), parses with `ast`, rejects unsupported nodes, admits `ast.Call` only for registered names with the declared arity, allows `ast.Name` only for `pi`/`e`, and evaluates with `__builtins__` disabled. Extend the whitelist and the AST allowlist together — never replace this with a plain `eval`.

Note that `%` is Python modulo, not percent: the UI's `%` key only succeeds when it forms a complete modulo expression (e.g. `10%3`); `50%` is a syntax error in expression mode. The HTTP API's separate `a`/`b`/`op` form supports `op=%` directly — the UI itself has no a/b/op mode. Division and modulo by zero raise `DomainError` and return HTTP 400 in both request shapes. Implicit multiplication (`2pi`, `2 sin(30)`) is rejected; the UI inserts an explicit `*` when a user action would otherwise create adjacent operands.

### Frontend and skins

`UI/static/script.js` is a single vanilla script with four concerns:

- **Calculator state machine** (`currentInput`, `expression`, `waitingForNewValue`, `resultShown`, `pendingMultiply`, `angleMode`, `history`). `=` fetches `/api/calc?expression=...&angle_mode=...`; the result area renders the response `display`, while the expression stays visible. On failure the expression remains editable and the server `detail` is shown persistently — the old 800 ms auto-clear and `invalid` substitution were removed (the required FR-019 behavior change).
- **Angle mode and history**: DEG/RAD buttons update `#angle-mode-indicator` and are sent with every request. Successful evaluations append `expression = display` (plus the mode when `is_trigonometric` is true) to a session-only list capped at 50, newest first; entries are rendered with `textContent`, and `#clear-history` empties the list.
- **Scientific input**: function keys insert `name(` and auto-close open parentheses before an operator or `=`; `π`/`e` insert the constant with an explicit `*` when it follows an operand; `x²` appends `^2`; `±` toggles the trailing operand's sign. The keypad is grouped into numbers, arithmetic, scientific functions, and evaluation controls.
- **Keyboard input** (digits, operators, parentheses, `Enter`, `Escape`, `Backspace`) plus key-focus semantics: pointer clicks blur the key so a later physical `Enter` maps to `=`, while keyboard activation keeps focus for native behavior.
- **Runtime states**: `aria-busy` + `data-loading` during fetches, `.is-error` on the display, and a visually hidden live region for result/error announcements.
- **Skin controller** with precedence `?skin=` query param > `localStorage["calculator-skin"]` > `default`.

Themes:

- `UI/static/style.css` — base/default theme (`data-skin="default"`).
- `UI/static/skins/classic.css` — 1990s pocket-calculator skin.
- `UI/static/skins/modern.css` — futuristic 2030 skin.
- Contract and extension guide: `UI/static/skins/README.md`; requirements include `:focus-visible`, `:disabled`, `prefers-reduced-motion`, contrast, and the four-column key grid.

Adding a skin touches three places: the `<link>` and `<option>` in `index.html`, and the skin's CSS file. The `<option>` list is the registry — `script.js` derives `SKINS` from it, and the pre-paint inline script accepts any slug-shaped `?skin=`/stored value, so no separate name list needs updating. Skin CSS must be scoped under `html[data-skin="<name>"]`; it is always loaded alongside the base stylesheet.

`../.claude/commands/calc-skin.md` still describes four registration points (a "pre-paint `skins` array" and a literal `SKINS` list). Those do not exist; the three places above are authoritative. It is otherwise a good checklist (states, README, tests).

### Climate Trends tool

`UI/climate.py` is the whole climate domain layer, shared by both servers. It defines eight representative regions and two measures:

- `temperature` — annual mean of daily `temperature_2m_mean`, in °C.
- `rainfall` — annual sum of daily `precipitation_sum`, in mm.

`GET /api/climate/options` returns the regions, measures, fixed period (1950–2025), and source metadata. `GET /api/climate/trend?region=<id>&measure=<id>` returns the annual series, regression output, and ready-to-display interpretation text; the frontend never computes statistics. Input errors raise `ClimateInputError` (HTTP 400); download/aggregation failures raise `ClimateDataError` (HTTP 502). Flask renders both as `{"success": false, "detail": ...}`; FastAPI as `{"detail": ...}`.

Data comes from the Open-Meteo Archive API (ERA5 reanalysis). Each region is downloaded once as daily data, reduced to annual aggregates, and cached in `UI/data/climate/<region>.json`; the checked-in caches make the UI work offline and avoid API rate limits. Years need at least `MIN_VALID_DAYS` (330) valid days to be kept, and trends need `MIN_TREND_YEARS` (20) annual records. The cache directory can be overridden with `CLIMATE_CACHE_DIR` (read at import time). `load_region_series` also keeps an in-process memory cache, so deleting a cache file only takes effect after a server restart; that is the normal way to force a fresh download.

Adding a region only requires an entry in `REGIONS` (the cache is created on first request; the frontend populates its selects from `/api/climate/options`). Adding a measure is more involved: `_download_region` requests only `temperature_2m_mean,precipitation_sum`, and `_aggregate_annual` hardcodes those two variables, so a new measure needs download/aggregation changes as well as a `MEASURES` entry.

The trend is ordinary least squares on year → annual value. The reported p-value uses a two-sided t-test with Newey–West (Bartlett) HAC standard errors (lag computed from record length) so serial correlation in annual values does not make the test overconfident. `UI/climate.py` implements the t distribution in pure Python; do not add numpy/scipy just for this. The 95% confidence interval uses the exact t critical value. A perfectly flat series falls back to classical OLS standard errors.

`UI/static/climate.html`, `climate.css`, and `climate.js` are the frontend. The chart is hand-built SVG in `climate.js` (no chart library), renders at the container's actual pixel width via `ResizeObserver`, supports pointer hover plus arrow-key inspection, and includes a data-table fallback and CSV download. `requestId` guards against stale responses. The page is linked from the calculator via `.tool-link`; the climate page links back to `/`.

## Tests

`UI/tests/conftest.py` puts `UI/` on `sys.path`, so tests import the Flask server as `app`, the FastAPI app as `calculator`, and the domain layers as `calc_engine` and `climate`. The 139 tests cover the engine (formatter, alias resolution, evaluator safety, error taxonomy, scientific functions, both angle modes), `/api/calc` integration on both servers (`fastapi.testclient.TestClient`, which needs the `httpx` test dependency), static skin/angle-mode/history wiring and CSS scoping, plus the climate domain (t distribution, aggregation, trend detection) and the Flask climate routes. Climate tests monkeypatch `climate.load_region_series`, so they never touch the network.

## Claude tooling

The parent `../.claude/` directory defines the project's validation workflow:

- `skills/playwright-validation/SKILL.md` — real-browser validation. Prefer the `mcp__playwrigt__*` tools; if Chromium/Chrome cannot launch, fall back to direct Playwright from a cached browser rather than retrying. It owns server reuse/startup, calculator flows (`7 × 8 = 56`, division-by-zero error + reset, chaining, keyboard, skins), accessibility, responsive checks at 375/768/1440 widths, screenshot evidence, and cleanup.
- `agents/ui-reviewer.md` — report-only reviewer; run it after changes to `UI/static/` or either backend. It must not edit code or touch Git.
- `commands/calc-skin.md` — `/calc-skin <name | brief>` to add a skin and route it through `ui-reviewer`.

Follow these procedures rather than improvising browser tests.

## Git

Remote: `git@github.com:mabdels-CSCE4301/sensor-monitor.git`. Local branches are `main`, `development`, and `staging`; the remote has `main` and `development`. Verified state: `development` and `staging` are both ancestors of `main` (main is ahead by 12 and 14 commits), and one stash entry from a branch-switch exercise exists. Branches, the stash, and history are part of the coursework — do not rewrite, reset, rebase, or clean up history, and do not commit, check out, or stash unless the user explicitly asks.
