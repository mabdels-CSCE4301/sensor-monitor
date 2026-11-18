"""Unit tests for the shared calculation engine (`UI/calc_engine.py`)."""

import math

import pytest

import calc_engine
from calc_engine import (
    DomainError,
    EvaluationResult,
    InvalidExpressionError,
    OverflowCalcError,
    apply_operation,
    evaluate,
    format_result,
    get_operation,
    normalize_angle_mode,
    safe_numeric,
)


# --- Formatter ------------------------------------------------------------


def test_format_uses_twelve_significant_digits():
    assert format_result(1 / 3) == "0.333333333333"
    assert format_result(123456789012.0) == "123456789012"


def test_format_strips_trailing_zeros():
    assert format_result(12.0) == "12"
    assert format_result(1.2300) == "1.23"


def test_format_never_emits_negative_zero():
    assert format_result(0.0) == "0"
    assert format_result(-0.0) == "0"


def test_format_collapses_very_small_values_to_zero():
    assert format_result(calc_engine.ZERO_DISPLAY_THRESHOLD / 10) == "0"


def test_format_uses_scientific_notation_for_large_magnitudes():
    assert format_result(1e13) == "1e+13"


def test_format_rejects_non_finite_values():
    with pytest.raises(OverflowCalcError):
        format_result(float("inf"))
    with pytest.raises(OverflowCalcError):
        format_result(10**400)


# --- Registry and arithmetic ---------------------------------------------


@pytest.mark.parametrize(
    "key, name",
    [
        ("+", "add"),
        ("add", "add"),
        ("plus", "add"),
        ("-", "subtract"),
        ("minus", "subtract"),
        ("*", "multiply"),
        ("x", "multiply"),
        ("multiply", "multiply"),
        ("/", "divide"),
        ("divide", "divide"),
        ("÷", "divide"),
        ("%", "modulo"),
        ("mod", "modulo"),
        ("modulo", "modulo"),
        ("**", "power"),
        ("^", "power"),
        ("power", "power"),
    ],
)
def test_alias_resolution(key, name):
    assert get_operation(key).name == name


def test_unknown_operation_is_rejected():
    with pytest.raises(InvalidExpressionError):
        get_operation("nope")


def test_apply_operation_preserves_alias_behavior():
    assert apply_operation(7, 8, "*") == 56.0
    assert apply_operation(7, 8, "x") == 56.0
    assert apply_operation(7, 8, "multiply") == 56.0
    assert apply_operation(7, 8, "÷") == 0.875


def test_apply_operation_rejects_division_by_zero():
    with pytest.raises(DomainError):
        apply_operation(5, 0, "/")
    with pytest.raises(DomainError):
        apply_operation(5, 0, "%")


# --- Arithmetic expressions ----------------------------------------------


def test_precedence_and_parentheses():
    assert evaluate("2+3*4").display == "14"
    assert evaluate("(2+3)*4").display == "20"


def test_unary_minus_and_decimal_input():
    assert evaluate("-5+2").display == "-3"
    assert evaluate("1.5+2.25").display == "3.75"


def test_exponentiation_associativity_and_unary_minus_binding():
    assert evaluate("2^3^2").display == "512"
    assert evaluate("-2^2").display == "-4"


def test_long_flat_expression_is_not_treated_as_deep_nesting():
    expression = "1+" * 100 + "1"
    assert evaluate(expression).display == "101"


# --- Evaluation result metadata ------------------------------------------


def test_evaluation_result_reports_trigonometry_and_mode():
    result = evaluate("sin(30)", "DEG")
    assert isinstance(result, EvaluationResult)
    assert result.display == "0.5"
    assert result.angle_mode == "DEG"
    assert result.is_trigonometric is True

    plain = evaluate("2+2")
    assert plain.is_trigonometric is False
    assert plain.angle_mode == "DEG"


# --- Evaluator safety -----------------------------------------------------


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "(1).real",
        "[1, 2]",
        "foo(1)",
        "pi(2)",
        "sqrt(1, 2)",
        "2pi",
        "2 sin(30)",
        "2(3)",
    ],
)
def test_unsafe_or_malformed_expressions_are_rejected(expression):
    with pytest.raises(InvalidExpressionError):
        evaluate(expression)


def test_abs_works_with_builtins_disabled():
    assert evaluate("abs(-7)").display == "7"


def test_over_length_and_over_nested_expressions_are_rejected():
    with pytest.raises(InvalidExpressionError):
        evaluate("1" * (calc_engine.MAX_EXPRESSION_LENGTH + 1))
    with pytest.raises(InvalidExpressionError):
        evaluate("(" * 40 + "1" + ")" * 40)


# --- Error taxonomy -------------------------------------------------------


def test_division_by_zero_is_a_domain_error():
    with pytest.raises(DomainError):
        evaluate("5/0")


@pytest.mark.parametrize("expression", ["2+", "(2+3", "", "   "])
def test_incomplete_expressions_are_invalid(expression):
    with pytest.raises(InvalidExpressionError):
        evaluate(expression)


def test_overflow_is_reported_as_overflow():
    with pytest.raises(OverflowCalcError):
        evaluate("2^100000")


def test_error_messages_leak_no_internals():
    forbidden = [
        "SyntaxError",
        "ZeroDivisionError",
        "ValueError",
        "OverflowError",
        "Traceback",
        "Traceback (most recent call last)",
    ]
    for expression in ["5/0", "2+", "sqrt(-1)", "2^100000", "foo(1)"]:
        with pytest.raises(calc_engine.CalcError) as info:
            evaluate(expression)
        message = info.value.detail
        assert message, "every error needs a user-facing detail"
        for token in forbidden:
            assert token not in message


def test_safe_numeric_rejects_non_numeric_and_non_finite():
    with pytest.raises(InvalidExpressionError):
        safe_numeric("abc")
    with pytest.raises(InvalidExpressionError):
        safe_numeric("inf")


# --- Scientific functions and constants ----------------------------------


def test_scientific_functions_normal_cases():
    assert evaluate("sqrt(16)").display == "4"
    assert evaluate("square(7)").display == "49"
    assert evaluate("power(2, 8)").display == "256"
    assert evaluate("exp(1)").value == pytest.approx(math.e, rel=1e-12)
    assert evaluate("ln(e)").display == "1"
    assert evaluate("log(1000)").display == "3"
    assert evaluate("abs(-7)").display == "7"


def test_constants_are_available_and_nestable():
    assert evaluate("pi").value == pytest.approx(math.pi)
    assert evaluate("e").value == pytest.approx(math.e)
    assert evaluate("sqrt(pi)").display == "1.77245385091"
    assert evaluate("sqrt(abs(-16))").display == "4"


@pytest.mark.parametrize(
    "expression",
    ["sqrt(-1)", "ln(0)", "ln(-5)", "log(0)", "log(-5)"],
)
def test_scientific_domain_errors(expression):
    with pytest.raises(DomainError):
        evaluate(expression)


# --- Trigonometry and angle modes ----------------------------------------


@pytest.mark.parametrize(
    "expression, display",
    [
        ("sin(0)", "0"),
        ("sin(30)", "0.5"),
        ("sin(45)", "0.707106781187"),
        ("sin(90)", "1"),
        ("cos(0)", "1"),
        ("cos(60)", "0.5"),
        ("tan(45)", "1"),
        ("asin(0.5)", "30"),
        ("acos(0.5)", "60"),
        ("atan(1)", "45"),
    ],
)
def test_degree_mode_trigonometry(expression, display):
    result = evaluate(expression, "DEG")
    assert result.display == display
    assert result.angle_mode == "DEG"
    assert result.is_trigonometric is True


@pytest.mark.parametrize(
    "expression, display",
    [
        ("sin(0)", "0"),
        ("sin(pi/6)", "0.5"),
        ("cos(pi/3)", "0.5"),
        ("tan(pi/4)", "1"),
        ("asin(0.5)", "0.523598775598"),
        ("atan(1)", "0.785398163397"),
    ],
)
def test_radian_mode_trigonometry(expression, display):
    result = evaluate(expression, "RAD")
    assert result.display == display
    assert result.angle_mode == "RAD"


@pytest.mark.parametrize(
    "expression",
    ["tan(90)", "tan(pi/2)", "asin(2)", "asin(-2)", "acos(-2)"],
)
def test_trig_domain_errors(expression):
    mode = "RAD" if "pi" in expression else "DEG"
    with pytest.raises(DomainError):
        evaluate(expression, mode)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("deg", "DEG"),
        ("RAD", "RAD"),
        (" Rad ", "RAD"),
        (None, "DEG"),
        ("", "DEG"),
    ],
)
def test_normalize_angle_mode(value, expected):
    assert normalize_angle_mode(value) == expected


def test_invalid_angle_mode_is_rejected():
    with pytest.raises(InvalidExpressionError):
        normalize_angle_mode("grad")
    with pytest.raises(InvalidExpressionError):
        evaluate("sin(30)", "grad")
