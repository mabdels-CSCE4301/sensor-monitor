from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Modern Calculator", version="1.0.0")


def _safe_numeric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def _evaluate_expression(expression: str) -> float:
    sanitized = expression.strip()
    if not sanitized:
        raise ValueError("Expression is empty")

    sanitized = sanitized.replace("×", "*").replace("÷", "/").replace("^", "**")
    if not re.fullmatch(r"[0-9\s+\-*/().%]+", sanitized):
        raise ValueError("Expression contains unsupported characters")

    try:
        tree = ast.parse(sanitized, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid arithmetic expression") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name, ast.Subscript, ast.List, ast.Tuple, ast.Dict, ast.Set)):
            raise ValueError("Expression contains unsupported syntax")

    compiled = compile(tree, filename="<calculator>", mode="eval")
    result = eval(compiled, {"__builtins__": {}}, {})

    if isinstance(result, (int, float)):
        return float(result)
    raise ValueError("Expression did not evaluate to a number")


def _apply_operation(left: float, right: float, operator: str) -> float:
    op = operator.strip().lower()
    operations = {
        "+": lambda a, b: a + b,
        "add": lambda a, b: a + b,
        "plus": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "subtract": lambda a, b: a - b,
        "minus": lambda a, b: a - b,
        "*": lambda a, b: a * b,
        "x": lambda a, b: a * b,
        "multiply": lambda a, b: a * b,
        "/": lambda a, b: a / b,
        "divide": lambda a, b: a / b,
        "÷": lambda a, b: a / b,
        "%": lambda a, b: a % b,
        "mod": lambda a, b: a % b,
        "modulo": lambda a, b: a % b,
        "**": lambda a, b: a ** b,
        "^": lambda a, b: a ** b,
        "power": lambda a, b: a ** b,
    }

    if op not in operations:
        raise ValueError(f"Unsupported operator: {operator}")

    if op in {"/", "divide", "÷"} and right == 0:
        raise ZeroDivisionError("Division by zero is not allowed")

    return float(operations[op](left, right))


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.api_route("/api/calc", methods=["GET", "POST"])
async def calc(request: Request, expression: str | None = None, a: float | None = None, b: float | None = None, op: str | None = None) -> JSONResponse:
    payload: dict[str, Any] = {}

    if request.method == "POST":
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    if expression is None:
        expression = payload.get("expression")
    if a is None:
        a = payload.get("a")
    if b is None:
        b = payload.get("b")
    if op is None:
        op = payload.get("op") or payload.get("operator")

    try:
        if expression is not None:
            result = _evaluate_expression(str(expression))
            return JSONResponse({"success": True, "result": result, "expression": str(expression)})

        if a is None or b is None or op is None:
            raise ValueError("Provide either expression or a, b, and op")

        left = _safe_numeric(a)
        right = _safe_numeric(b)
        result = _apply_operation(left, right, str(op))
        return JSONResponse({"success": True, "result": result, "a": left, "b": right, "op": str(op)})
    except ZeroDivisionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run("calculator:app", host="0.0.0.0", port=8000, reload=True)
