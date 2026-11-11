# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Course project for "AI-Assisted Software Development with VS Code, Git, Claude & GitHub Spec Kit". The application is a **calculator**: a Flask server (`UI/app.py`, primary) or a FastAPI port (`UI/calculator.py`) exposing one arithmetic API, plus a dependency-free HTML/CSS/JS frontend. `README.md` is course metadata (date, author, milestones), not app documentation. The repo's Git history and branches are themselves coursework artifacts — never rewrite, reset, or clean up history.

Despite the directory name, there is no sensor-monitoring code.

## Commands

Run from the repository root (`sensor-monitor/`). There is no build step, linter, or checked-in virtualenv; dependencies in `UI/requirements.txt` are unpinned.

```bash
pip install -r UI/requirements.txt

python3 UI/app.py            # Flask calculator   → http://localhost:5000 (debug reloader)
python3 UI/calculator.py     # FastAPI calculator → http://localhost:8000 (uvicorn reload)
python3 UI/sample.py         # duplicate Flask entry point, also port 5000

python3 -m pytest UI/tests -q
python3 -m pytest UI/tests/test_static.py::test_modern_skin_is_served_and_scoped -q   # one test
```

Ports 5000/8000 are hardcoded, so run one server at a time unless you change the port. Both servers serve `UI/static/` from the same origin as `/api/calc`, so the frontend needs no CORS setup.

Smoke-test the API without a browser:

```bash
curl -s 'http://localhost:5000/api/calc?expression=2+3*4'
curl -s 'http://localhost:5000/api/calc?a=7&b=8&op=multiply'
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

Note that `%` is Python modulo, not percent: `50%` is a syntax error. The UI's `%` key only succeeds when it forms a complete modulo expression (e.g. `10%3`); use the `a`/`b`/`op` mode for `op=%`. In that mode division by zero is rejected before the operation; in expression mode Python raises `ZeroDivisionError`, which both servers convert to HTTP 400.

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

Adding a skin touches four places: the `<link>` and `<option>` in `index.html`, the pre-paint `skins` array in `index.html`, and `SKINS` in `script.js`. Skin CSS must be scoped under `html[data-skin="<name>"]`; it is always loaded alongside the base stylesheet.

## Tests

`UI/tests/conftest.py` puts `UI/` on `sys.path`, so tests import the servers as `app`. The current tests cover static skin wiring and CSS scoping only — there are no arithmetic/API tests yet. Add API tests through Flask's `app.test_client()`.

## Git

Remote: `git@github.com:mabdels-CSCE4301/sensor-monitor.git`. Local branches include `main`, `development`, and `staging`; the remote has `main` and `development`. `development` is an ancestor of `main` without the calculator UI, and a stash from a branch-switch exercise may exist. Branches, the stash, and history are part of the coursework.
