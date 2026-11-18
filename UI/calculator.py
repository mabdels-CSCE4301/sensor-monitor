from __future__ import annotations

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Modern Calculator", version="1.0.0")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/climate")
async def climate_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "climate.html")


@app.get("/api/climate/options")
async def climate_options() -> JSONResponse:
    return JSONResponse(get_options())


@app.get("/api/climate/trend")
async def climate_trend(region: str = "", measure: str = "") -> JSONResponse:
    try:
        return JSONResponse(build_trend(region.strip(), measure.strip()))
    except ClimateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.api_route("/api/calc", methods=["GET", "POST"])
async def calc(
    request: Request,
    expression: str | None = None,
    a: str | None = None,
    b: str | None = None,
    op: str | None = None,
    operator: str | None = None,
    angle_mode: str | None = None,
) -> JSONResponse:
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
        op = operator if operator is not None else (
            payload.get("op") or payload.get("operator")
        )
    if angle_mode is None:
        angle_mode = payload.get("angle_mode")

    try:
        mode = normalize_angle_mode(angle_mode)

        if expression is not None:
            result = evaluate(str(expression), mode)
            return JSONResponse(
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
        return JSONResponse(
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
        raise HTTPException(status_code=400, detail=exc.detail) from exc


if __name__ == "__main__":
    uvicorn.run("calculator:app", host="0.0.0.0", port=8000, reload=True)
