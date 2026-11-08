import ast
import re
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")


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


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/calc", methods=["GET", "POST"])
def calc():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = request.args.to_dict()

    expression = payload.get("expression")
    a = payload.get("a")
    b = payload.get("b")
    op = payload.get("op") or payload.get("operator")

    try:
        if expression is not None:
            result = _evaluate_expression(str(expression))
            return jsonify({"success": True, "result": result, "expression": str(expression)})

        if a is None or b is None or op is None:
            raise ValueError("Provide either expression or a, b, and op")

        left = _safe_numeric(a)
        right = _safe_numeric(b)
        result = _apply_operation(left, right, str(op))
        return jsonify({"success": True, "result": result, "a": left, "b": right, "op": str(op)})
    except ZeroDivisionError as exc:
        return jsonify({"success": False, "detail": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"success": False, "detail": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
