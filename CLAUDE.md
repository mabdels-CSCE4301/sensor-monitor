# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Course project for "AI-Assisted Software Development with VS Code, Git, Claude & GitHub Spec Kit". The working application is a **calculator**: a Flask (or FastAPI) backend exposing an arithmetic API plus a vanilla HTML/CSS/JS frontend. The repo's Git history and multiple branches are themselves part of the coursework (branching, conflict-resolution exercises), so avoid rewriting or cleaning up history.

Despite the directory name, there is no sensor-monitoring code.

## Layout

- `UI/` — the entire application (there is no package/`__init__.py`; `UI/` is effectively the app root).
  - `app.py` — Flask server, currently the primary implementation.
  - `calculator.py` — FastAPI port with the same arithmetic helpers duplicated.
  - `sample.py` — thin alias that runs the Flask app.
  - `static/` — calculator frontend (`index.html`, `script.js`, `style.css`).
  - `tests/` — pytest setup; `conftest.py` puts `UI/` on `sys.path`. No test files currently exist.
  - `requirements.txt` — unpinned deps: fastapi, uvicorn, flask, requests, pytest.
- `src/`, `tests/`, `docs/` at the repo root are empty placeholders.

## Commands

Run from the repository root (`sensor-monitor/`).

```bash
pip install -r UI/requirements.txt          # dependencies (no venv checked in)

python3 UI/app.py                           # Flask calculator  → http://localhost:5000
python3 UI/calculator.py                    # FastAPI calculator → http://localhost:8000 (reload enabled)
python3 UI/sample.py                        # duplicate Flask entry point on port 5000

python3 -m pytest UI/tests -q               # full test suite (none yet; reports "no tests ran")
```

`UI/tests/conftest.py` inserts `UI/` into `sys.path`, so tests import the server as `app`. Run test commands from the repo root or from `UI/`; both work.

## Architecture notes

### API contract (`/api/calc`, GET or POST)

Accepts either:
- `expression` — an arithmetic string such as `"2+3*4"`, or
- `a`, `b`, `op` — two numbers and an operator.

Success: `{"success": true, "result": <float>, ...}`. Failure: HTTP 400 with `{"success": false, "detail": "<message>"}` (FastAPI returns its standard `{"detail": ...}` body via `HTTPException`).

`op` accepts both symbols and aliases: `+ add plus`, `- subtract minus`, `* x multiply`, `/ divide ÷`, `% mod modulo`, `** ^ power`. Division by zero is rejected explicitly before evaluation.

### Expression safety

`_evaluate_expression` sanitizes unicode operators (`×`, `÷`, `^`), enforces a character whitelist, parses with `ast`, rejects `Call`/`Attribute`/`Name`/subscript/collection nodes, then `eval`s with `__builtins__` disabled. Preserve this pattern when extending expression support — do not loosen it to a plain `eval`.

### Keeping the two servers in sync

`app.py` and `calculator.py` contain byte-for-byte copies of `_safe_numeric`, `_evaluate_expression`, and `_apply_operation`. Any arithmetic or operator change must be made in **both** files. The frontend (`UI/static/script.js`) calls `fetch('/api/calc?expression=...')`, so whichever server is launched must serve `static/` from the same origin.

## Git

Remote: `git@github.com:mabdels-CSCE4301/sensor-monitor.git`. Branches `main`, `development`, and `staging` exist; `development` is an ancestor of `main` without the calculator UI, and there is a stash from a branch-switch exercise. Working tree is normally clean on `main`.
