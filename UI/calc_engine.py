"""Shared calculation engine for the calculator application.

This module is the single owner of arithmetic, scientific operations, angle
handling, result formatting, and user-facing calculation errors. Both server
implementations (`app.py` for Flask and `calculator.py` for FastAPI) delegate
here; the frontend never computes mathematics.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any, Callable

DEFAULT_ANGLE_MODE = "DEG"
ANGLE_MODES = ("DEG", "RAD")
MAX_EXPRESSION_LENGTH = 256
MAX_NESTING_DEPTH = 32
SIGNIFICANT_DIGITS = 12
ZERO_DISPLAY_THRESHOLD = 1e-12
TAN_DOMAIN_EPSILON = 1e-12

# Exponent magnitudes beyond this cannot produce a displayable real number and
# would otherwise force Python to build an enormous integer.
_MAX_EXPONENT = 100_000

_CHARACTER_WHITELIST = re.compile(r"[0-9A-Za-z+\-*/%().,\s]+")
_UNICODE_REPLACEMENTS = (("×", "*"), ("÷", "/"), ("−", "-"), ("π", "pi"), ("^", "**"))
_BINARY_OPERATORS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Mod: "%",
    ast.Pow: "**",
}


class CalcError(Exception):
    """Base class for every user-facing calculation error."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidExpressionError(CalcError):
    """The expression cannot be parsed or is not supported."""


class DomainError(CalcError):
    """The operation is mathematically undefined for the given input."""


class OverflowCalcError(CalcError):
    """The result cannot be represented or displayed."""


@dataclass(frozen=True)
class Operation:
    """One named, individually testable operation in the registry."""

    name: str
    symbol: str | None
    aliases: tuple[str, ...]
    arity: int
    impl: Callable[..., float]
    angle_aware: bool = False
    domain: str = "real"


@dataclass(frozen=True)
class EvaluationResult:
    """Everything the API and UI need to know about one evaluation."""

    value: float
    display: str
    angle_mode: str
    is_trigonometric: bool


OPERATIONS: dict[str, Operation] = {}
_LOOKUP: dict[str, Operation] = {}


def register(operation: Operation) -> Operation:
    """Register an operation under its name, symbol, and aliases."""
    OPERATIONS[operation.name] = operation
    keys = [operation.name]
    if operation.symbol:
        keys.append(operation.symbol)
    keys.extend(operation.aliases)
    for key in keys:
        _LOOKUP[key.strip().lower()] = operation
    return operation


def get_operation(name_or_symbol: str) -> Operation:
    """Resolve a function name, operator symbol, or alias, case-insensitively."""
    key = str(name_or_symbol).strip().lower()
    try:
        return _LOOKUP[key]
    except KeyError as exc:
        raise InvalidExpressionError(f"Unsupported operation: {name_or_symbol}") from exc


# --- Arithmetic -----------------------------------------------------------


def _divide(left: float, right: float) -> float:
    if right == 0:
        raise DomainError("Cannot divide by zero")
    return left / right


def _modulo(left: float, right: float) -> float:
    if right == 0:
        raise DomainError("Cannot divide by zero")
    return left % right


def _power(left: float, right: float) -> float:
    if abs(right) > _MAX_EXPONENT:
        raise OverflowCalcError("Result is too large to display")
    return left**right


register(Operation("add", "+", ("plus",), 2, lambda a, b: a + b))
register(Operation("subtract", "-", ("minus",), 2, lambda a, b: a - b))
register(Operation("multiply", "*", ("x",), 2, lambda a, b: a * b))
register(Operation("divide", "/", ("÷",), 2, _divide))
register(Operation("modulo", "%", ("mod",), 2, _modulo))
register(Operation("power", "**", ("^", "pow", "xʸ"), 2, _power))


# --- Scientific functions -------------------------------------------------


def _sqrt(value: float) -> float:
    if value < 0:
        raise DomainError("Square root of a negative number is not defined")
    return math.sqrt(value)


def _square(value: float) -> float:
    return value * value


def _exp(value: float) -> float:
    try:
        return math.exp(value)
    except OverflowError as exc:
        raise OverflowCalcError("Result is too large to display") from exc


def _natural_log(value: float) -> float:
    if value <= 0:
        raise DomainError("Natural log is defined only for positive numbers")
    return math.log(value)


def _base10_log(value: float) -> float:
    if value <= 0:
        raise DomainError("Log is defined only for positive numbers")
    return math.log10(value)


def _absolute(value: Any) -> float:
    return abs(value)


def _to_radians(value: float, angle_mode: str) -> float:
    return math.radians(value) if angle_mode == "DEG" else value


def _from_radians(value: float, angle_mode: str) -> float:
    return math.degrees(value) if angle_mode == "DEG" else value


def _sin(value: float, angle_mode: str) -> float:
    return math.sin(_to_radians(value, angle_mode))


def _cos(value: float, angle_mode: str) -> float:
    return math.cos(_to_radians(value, angle_mode))


def _tan(value: float, angle_mode: str) -> float:
    radians = _to_radians(value, angle_mode)
    if abs(math.cos(radians)) < TAN_DOMAIN_EPSILON:
        raise DomainError("Tangent is undefined at this angle")
    return math.tan(radians)


def _asin(value: float, angle_mode: str) -> float:
    if not -1 <= value <= 1:
        raise DomainError("Inverse sine is defined only between -1 and 1")
    return _from_radians(math.asin(value), angle_mode)


def _acos(value: float, angle_mode: str) -> float:
    if not -1 <= value <= 1:
        raise DomainError("Inverse cosine is defined only between -1 and 1")
    return _from_radians(math.acos(value), angle_mode)


def _atan(value: float, angle_mode: str) -> float:
    return _from_radians(math.atan(value), angle_mode)


register(Operation("sqrt", None, ("√",), 1, _sqrt))
register(Operation("square", None, ("x²", "sqr"), 1, _square))
register(Operation("exp", None, ("eˣ",), 1, _exp))
register(Operation("ln", None, (), 1, _natural_log))
register(Operation("log", None, ("log10",), 1, _base10_log))
register(Operation("abs", None, (), 1, _absolute))
register(Operation("sin", None, (), 1, _sin, angle_aware=True))
register(Operation("cos", None, (), 1, _cos, angle_aware=True))
register(Operation("tan", None, (), 1, _tan, angle_aware=True))
register(Operation("asin", None, (), 1, _asin, angle_aware=True))
register(Operation("acos", None, (), 1, _acos, angle_aware=True))
register(Operation("atan", None, (), 1, _atan, angle_aware=True))


# --- Formatting and numeric helpers ---------------------------------------


def _finalize_number(value: Any) -> float:
    """Coerce a result to a finite real float or raise a controlled error."""
    if isinstance(value, complex):
        raise DomainError("Result is not a real number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OverflowCalcError("Result is too large to display") from exc
    if not math.isfinite(number):
        raise OverflowCalcError("Result is too large to display")
    return number


def format_result(value: Any) -> str:
    """Render a number with up to 12 significant digits and no negative zero."""
    number = _finalize_number(value)
    if number == 0 or abs(number) < ZERO_DISPLAY_THRESHOLD:
        return "0"
    text = f"{number:.{SIGNIFICANT_DIGITS}g}"
    return "0" if text in ("-0", "-0.0") else text


def safe_numeric(value: Any) -> float:
    """Parse an API numeric field, raising a controlled error when invalid."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidExpressionError(f"Invalid numeric value: {value!r}") from exc
    if not math.isfinite(number):
        raise InvalidExpressionError("Numeric values must be finite")
    return number


def normalize_angle_mode(value: Any = None) -> str:
    """Normalize a user-supplied angle mode to DEG or RAD (DEG by default)."""
    if value is None:
        return DEFAULT_ANGLE_MODE
    text = str(value).strip().upper()
    if not text:
        return DEFAULT_ANGLE_MODE
    if text in ANGLE_MODES:
        return text
    raise InvalidExpressionError("Angle mode must be DEG or RAD")


def apply_operation(left: float, right: float, operator: str) -> float:
    """Apply a registered binary operation by symbol or alias."""
    operation = get_operation(operator)
    if operation.arity != 2:
        raise InvalidExpressionError(f"{operation.name} does not take two operands")
    try:
        result = operation.impl(left, right)
    except CalcError:
        raise
    except ZeroDivisionError as exc:
        raise DomainError("Cannot divide by zero") from exc
    except OverflowError as exc:
        raise OverflowCalcError("Result is too large to display") from exc
    except (TypeError, ValueError) as exc:
        raise DomainError("The operation is not defined for these values") from exc
    return _finalize_number(result)


# --- Expression evaluation -------------------------------------------------


def _normalize_expression(expression: str) -> str:
    text = expression
    for source, replacement in _UNICODE_REPLACEMENTS:
        text = text.replace(source, replacement)
    return text


def _parenthesis_depth(text: str) -> int:
    """Maximum parenthesis nesting depth.

    Function calls and explicit parentheses are the only nesting the grammar
    permits; counting binary-operator chain depth here would wrongly reject a
    long flat expression such as ``1+2+3+...``.
    """
    depth = 0
    maximum = 0
    for char in text:
        if char == "(":
            depth += 1
            maximum = max(maximum, depth)
        elif char == ")":
            depth -= 1
    return maximum


def _evaluate_call(node: ast.Call, context: dict[str, Any]) -> float:
    if not isinstance(node.func, ast.Name):
        raise InvalidExpressionError("Unsupported function call")
    if node.keywords or any(isinstance(arg, ast.Starred) for arg in node.args):
        raise InvalidExpressionError("Unsupported function call")

    operation = get_operation(node.func.id)
    if len(node.args) != operation.arity:
        raise InvalidExpressionError(
            f"{operation.name} expects {operation.arity} argument(s)"
        )

    values = [_evaluate_node(arg, context) for arg in node.args]
    try:
        if operation.angle_aware:
            context["is_trigonometric"] = True
            result = operation.impl(values[0], context["angle_mode"])
        else:
            result = operation.impl(*values)
    except CalcError:
        raise
    except ZeroDivisionError as exc:
        raise DomainError("Cannot divide by zero") from exc
    except OverflowError as exc:
        raise OverflowCalcError("Result is too large to display") from exc
    except (TypeError, ValueError) as exc:
        raise DomainError("The operation is not defined for these values") from exc
    return _finalize_number(result)


def _evaluate_node(node: ast.AST, context: dict[str, Any]) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body, context)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise InvalidExpressionError("Expression must use numbers")
        return node.value

    if isinstance(node, ast.Name):
        if node.id == "pi":
            return math.pi
        if node.id == "e":
            return math.e
        raise InvalidExpressionError(f"Unknown name: {node.id}")

    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_node(node.operand, context)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise InvalidExpressionError("Expression contains unsupported syntax")

    if isinstance(node, ast.BinOp):
        operator = _BINARY_OPERATORS.get(type(node.op))
        if operator is None:
            raise InvalidExpressionError("Expression contains unsupported syntax")
        left = _evaluate_node(node.left, context)
        right = _evaluate_node(node.right, context)
        return apply_operation(left, right, operator)

    if isinstance(node, ast.Call):
        return _evaluate_call(node, context)

    raise InvalidExpressionError("Expression contains unsupported syntax")


def evaluate(
    expression: str, angle_mode: str = DEFAULT_ANGLE_MODE
) -> EvaluationResult:
    """Evaluate an expression and return the numeric value plus display data."""
    mode = normalize_angle_mode(angle_mode)

    text = "" if expression is None else str(expression).strip()
    if not text:
        raise InvalidExpressionError("Enter an expression")

    normalized = _normalize_expression(text)
    if len(normalized) > MAX_EXPRESSION_LENGTH:
        raise InvalidExpressionError("Expression is too long")
    if not _CHARACTER_WHITELIST.fullmatch(normalized):
        raise InvalidExpressionError("Expression contains unsupported characters")

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise InvalidExpressionError("Enter a complete expression") from exc

    if _parenthesis_depth(normalized) > MAX_NESTING_DEPTH:
        raise InvalidExpressionError("Expression is nested too deeply")

    context: dict[str, Any] = {"angle_mode": mode, "is_trigonometric": False}
    try:
        value = _evaluate_node(tree.body, context)
    except CalcError:
        raise
    except ZeroDivisionError as exc:
        raise DomainError("Cannot divide by zero") from exc
    except OverflowError as exc:
        raise OverflowCalcError("Result is too large to display") from exc
    except (TypeError, ValueError) as exc:
        raise DomainError("The operation is not defined for these values") from exc

    number = _finalize_number(value)
    return EvaluationResult(
        value=number,
        display=format_result(number),
        angle_mode=mode,
        is_trigonometric=bool(context["is_trigonometric"]),
    )
