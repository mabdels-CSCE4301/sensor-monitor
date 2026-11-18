from flask import Flask, jsonify, request, send_from_directory

from calc_engine import (
    CalcError,
    InvalidExpressionError,
    apply_operation,
    evaluate,
    format_result,
    normalize_angle_mode,
    safe_numeric,
)
from climate import ClimateError, build_trend, get_options

app = Flask(__name__, static_folder="static")


@app.errorhandler(ClimateError)
def handle_climate_error(error: ClimateError):
    return jsonify({"success": False, "detail": str(error)}), error.status_code


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/climate")
def climate_page():
    return send_from_directory(app.static_folder, "climate.html")


@app.route("/api/climate/options")
def climate_options():
    return jsonify(get_options())


@app.route("/api/climate/trend")
def climate_trend():
    region = str(request.args.get("region", "")).strip()
    measure = str(request.args.get("measure", "")).strip()
    return jsonify(build_trend(region, measure))


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
    angle_mode = payload.get("angle_mode")

    try:
        mode = normalize_angle_mode(angle_mode)

        if expression is not None:
            result = evaluate(str(expression), mode)
            return jsonify(
                {
                    "success": True,
                    "result": result.value,
                    "display": result.display,
                    "expression": str(expression),
                    "angle_mode": result.angle_mode,
                    "is_trigonometric": result.is_trigonometric,
                }
            )

        if a is None or b is None or op is None:
            raise InvalidExpressionError("Provide either expression or a, b, and op")

        left = safe_numeric(a)
        right = safe_numeric(b)
        value = apply_operation(left, right, str(op))
        return jsonify(
            {
                "success": True,
                "result": value,
                "display": format_result(value),
                "a": left,
                "b": right,
                "op": str(op),
                "angle_mode": mode,
                "is_trigonometric": False,
            }
        )
    except CalcError as exc:
        return jsonify({"success": False, "detail": exc.detail}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
