# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Course project for "AI-Assisted Software Development with VS Code, Git, Claude & GitHub Spec Kit". The application is a **calculator** (`/`) plus a **Climate Trends explorer** (`/climate`): a Flask server (`UI/app.py`, primary) or a FastAPI port (`UI/calculator.py`) exposing arithmetic and climate APIs, plus dependency-free HTML/CSS/JS frontends. `README.md` is course metadata (date, author, milestones), not app documentation. The repo's Git history and branches are themselves coursework artifacts — never rewrite, reset, or clean up history.

Despite the directory name, there is no sensor-monitoring code. The climate feature analyses ERA5 reanalysis, not live sensors.

## Commands

Run from the repository root (`sensor-monitor/`). There is no build step, linter, or checked-in virtualenv; dependencies in `UI/requirements.txt` are unpinned.

```bash
pip install -r UI/requirements.txt

python3 UI/app.py            # Flask calculator   → http://localhost:5000 (debug reloader)
python3 UI/calculator.py     # FastAPI calculator → http://localhost:8000 (uvicorn reload)
python3 UI/sample.py         # duplicate Flask entry point, also port 5000

python3 -m pytest UI/tests -q
python3 -m pytest UI/tests/test_static.py::test_modern_skin_is_served_and_scoped -q   # one test
python3 -m pytest UI/tests/test_climate.py -q                                        # climate tools
```

Ports 5000/8000 are hardcoded, so run one server at a time unless you change the port. Both servers serve `UI/static/` from the same origin as `/api/calc` and `/api/climate/*`, so the frontends need no CORS setup.

Smoke-test the API without a browser:

```bash
curl -s 'http://localhost:5000/api/calc?expression=2+3*4'
curl -s 'http://localhost:5000/api/calc?a=7&b=8&op=multiply'
curl -s 'http://localhost:5000/api/climate/options'
curl -s 'http://localhost:5000/api/climate/trend?region=london&measure=temperature'
```

## Architecture

### One API, two server implementations

`/api/calc` (GET or POST; query params or JSON body) accepts either:

- `expression` — an arithmetic string such as `"2+3*4"`, or
- `a`, `b`, `op` — two numbers and an operator.

Flask success returns `{"success": true, "result": ...}`; Flask errors return HTTP 400 with `{"success": false, "detail": "..."}`. FastAPI success shapes match, but its 400s use FastAPI's `{"detail": "..."}` body via `HTTPException` (no `success` field). The frontend keys off the HTTP status and `detail`, so both work.

`op` accepts symbols and aliases: `+ add plus`, `- subtract minus`, `* x multiply`, `/ divide ÷`, `% mod modulo`, `** ^ power`.

`app.py` and `calculator.py` intentionally duplicate `_safe_numeric`, `_evaluate_expression`, and `_apply_operation` **byte-for-byte**. Any arithmetic or operator change must be made in **both** files or the servers diverge.

### Expression safety

`_evaluate_expression` normalizes unicode operators (`×`, `÷`, `^`), enforces a character whitelist (`[0-9 + - * / ( ) . % whitespace]`), parses with `ast`, rejects `Call`/`Attribute`/`Name`/subscript/collection nodes, then evaluates with `__builtins__` disabled. Preserve this pattern when extending expressions — never replace it with a plain `eval`.

Note that `%` is Python modulo, not percent: the UI's `%` key only succeeds when it forms a complete modulo expression (e.g. `10%3`); `50%` is a syntax error in expression mode. The HTTP API's separate `a`/`b`/`op` form supports `op=%` directly — the UI itself has no a/b/op mode. Division by zero is rejected before the operation in the `a`/`b`/`op` form; in expression mode Python raises `ZeroDivisionError`, which both servers convert to HTTP 400.

### Frontend and skins

`UI/static/script.js` is a single vanilla script with four concerns:

- **Calculator state machine** (`currentInput`, `expression`, `waitingForNewValue`, `resultShown`). `=` fetches `/api/calc`; failures render `Error` / `invalid`, then auto-clear after 800 ms.
- **Keyboard input** (digits, operators, `Enter`, `Escape`, `Backspace`) plus key-focus semantics: pointer clicks blur the key so a later physical `Enter` maps to `=`, while keyboard activation keeps focus for native behavior.
- **Runtime states**: `aria-busy` + `data-loading` during fetches, `.is-error` on the display, and a visually hidden live region for result/error announcements.
- **Skin controller** with precedence `?skin=` query param > `localStorage["calculator-skin"]` > `default`.

Themes:

- `UI/static/style.css` — base/default theme (`data-skin="default"`).
- `UI/static/skins/classic.css` — 1990s pocket-calculator skin.
- `UI/static/skins/modern.css` — futuristic 2030 skin.
- Contract and extension guide: `UI/static/skins/README.md`.

Adding a skin touches three places: the `<link>` and `<option>` in `index.html`, and the skin's CSS file. The `<option>` list is the registry — `script.js` derives `SKINS` from it, and the pre-paint script accepts any slug-shaped `?skin=`/stored value, so no separate name list needs updating. Skin CSS must be scoped under `html[data-skin="<name>"]`; it is always loaded alongside the base stylesheet.

### Climate Trends tool

`UI/climate.py` is the whole climate domain layer, shared by both servers. It defines eight representative regions and two measures:

- `temperature` — annual mean of daily `temperature_2m_mean`, in °C.
- `rainfall` — annual sum of daily `precipitation_sum`, in mm.

`GET /api/climate/options` returns the regions, measures, fixed period (1950–2025), and source metadata. `GET /api/climate/trend?region=<id>&measure=<id>` returns the annual series, regression output, and ready-to-display interpretation text. Flask errors use `{"success": false, "detail": ...}`; FastAPI uses `{"detail": ...}`.

Data comes from the Open-Meteo Archive API (ERA5 reanalysis). Each region is downloaded once as daily data, reduced to annual aggregates, and cached in `UI/data/climate/<region>.json`; the checked-in caches make the UI work offline and avoid API rate limits. Delete a region's cache to force a fresh download on its next request. The cache directory can be overridden with `CLIMATE_CACHE_DIR`.

The trend is ordinary least squares on year → annual value. The reported p-value uses a two-sided t-test with Newey–West (Bartlett) HAC standard errors (lag computed from record length) so serial correlation in annual values does not make the test overconfident. `UI/climate.py` implements the t distribution in pure Python; do not add numpy/scipy just for this. The 95% confidence interval uses the exact t critical value. Tests cover the p-value implementation, trend detection, aggregation, and both HTTP layers.

`UI/static/climate.html`, `climate.css`, and `climate.js` are the frontend. The chart is hand-built SVG in `climate.js` (no chart library), renders at the container's actual pixel width via `ResizeObserver`, supports pointer hover plus arrow-key inspection, and includes a data-table fallback and CSV download. The page is linked from the calculator via `.tool-link`; the climate page links back to `/`.

## Tests

`UI/tests/conftest.py` puts `UI/` on `sys.path`, so tests import the servers as `app`. Existing tests cover static skin wiring, CSS scoping, and the climate domain/API. There are no arithmetic/API tests yet. Add API tests through Flask's `app.test_client()`; climate tests monkeypatch `climate.load_region_series` so they never touch the network.

## Git

Remote: `git@github.com:mabdels-CSCE4301/sensor-monitor.git`. Local branches include `main`, `development`, and `staging`; the remote has `main` and `development`. `development` is an ancestor of `main` without the calculator UI, and a stash from a branch-switch exercise may exist. Branches, the stash, and history are part of the coursework.
