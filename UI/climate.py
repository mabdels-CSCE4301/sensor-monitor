"""Climate trend analysis for the Climate Trends tool.

Data is fetched once from the Open-Meteo Archive API (ERA5 reanalysis) and
cached as annual aggregates.  Keeping the raw daily payload out of the cache
makes the data small enough to ship and fast to read.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = Path(os.environ.get("CLIMATE_CACHE_DIR", BASE_DIR / "data" / "climate"))

START_YEAR = 1950
END_YEAR = 2025
MIN_VALID_DAYS = 330
MIN_TREND_YEARS = 20
ALPHA = 0.05

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = {
    "name": "ERA5 reanalysis",
    "provider": "Open-Meteo Archive API",
    "url": "https://open-meteo.com/en/docs/historical-weather-api",
    "note": (
        "Each region is represented by the ERA5 grid cell nearest its listed "
        "coordinates. Values are modelled reanalysis data, not a single weather "
        "station."
    ),
}

REGIONS: dict[str, dict[str, Any]] = {
    "london": {
        "id": "london",
        "name": "London",
        "country": "United Kingdom",
        "latitude": 51.5072,
        "longitude": -0.1276,
    },
    "sacramento": {
        "id": "sacramento",
        "name": "Sacramento",
        "country": "California, USA",
        "latitude": 38.5816,
        "longitude": -121.4944,
    },
    "manaus": {
        "id": "manaus",
        "name": "Manaus",
        "country": "Amazonas, Brazil",
        "latitude": -3.1190,
        "longitude": -60.0217,
    },
    "niamey": {
        "id": "niamey",
        "name": "Niamey",
        "country": "Niger",
        "latitude": 13.5116,
        "longitude": 2.1254,
    },
    "alice-springs": {
        "id": "alice-springs",
        "name": "Alice Springs",
        "country": "Northern Territory, Australia",
        "latitude": -23.6980,
        "longitude": 133.8807,
    },
    "mumbai": {
        "id": "mumbai",
        "name": "Mumbai",
        "country": "India",
        "latitude": 19.0760,
        "longitude": 72.8777,
    },
    "oslo": {
        "id": "oslo",
        "name": "Oslo",
        "country": "Norway",
        "latitude": 59.9139,
        "longitude": 10.7522,
    },
    "cape-town": {
        "id": "cape-town",
        "name": "Cape Town",
        "country": "South Africa",
        "latitude": -33.9249,
        "longitude": 18.4241,
    },
}

MEASURES: dict[str, dict[str, Any]] = {
    "temperature": {
        "id": "temperature",
        "label": "Mean temperature",
        "short_label": "Temperature",
        "variable": "temperature_2m_mean",
        "aggregation": "mean",
        "unit": "°C",
        "decade_unit": "°C per decade",
        "chart_label": "Annual mean temperature",
        "trend_noun": "annual mean temperature",
        "description": "Average of daily mean temperatures for each calendar year.",
    },
    "rainfall": {
        "id": "rainfall",
        "label": "Total rainfall",
        "short_label": "Rainfall",
        "variable": "precipitation_sum",
        "aggregation": "sum",
        "unit": "mm",
        "decade_unit": "mm per decade",
        "chart_label": "Annual rainfall total",
        "trend_noun": "annual rainfall",
        "description": "Sum of daily precipitation for each calendar year.",
    },
}


class ClimateError(Exception):
    """Base class for errors that the HTTP layer should turn into a response."""

    status_code = 400


class ClimateInputError(ClimateError):
    status_code = 400


class ClimateDataError(ClimateError):
    status_code = 502


_series_memory: dict[str, dict[str, Any]] = {}


def region_display(region: dict[str, Any]) -> str:
    return f"{region['name']}, {region['country']}"


def get_options() -> dict[str, Any]:
    """Return the regions, measures and fixed period used by the UI."""

    regions = [
        {
            "id": region["id"],
            "name": region["name"],
            "country": region["country"],
            "display": region_display(region),
            "latitude": region["latitude"],
            "longitude": region["longitude"],
        }
        for region in REGIONS.values()
    ]
    measures = [
        {
            "id": measure["id"],
            "label": measure["label"],
            "short_label": measure["short_label"],
            "unit": measure["unit"],
            "decade_unit": measure["decade_unit"],
            "chart_label": measure["chart_label"],
            "description": measure["description"],
        }
        for measure in MEASURES.values()
    ]
    return {
        "regions": regions,
        "measures": measures,
        "period": {"start_year": START_YEAR, "end_year": END_YEAR, "years": END_YEAR - START_YEAR + 1},
        "source": SOURCE,
    }


def _cache_path(region_id: str) -> Path:
    return CACHE_DIR / f"{region_id}.json"


def _valid_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _aggregate_annual(daily: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Turn daily ERA5 arrays into yearly temperature means and rainfall totals."""

    times = daily.get("time")
    temperatures = daily.get("temperature_2m_mean")
    precipitation = daily.get("precipitation_sum")
    if not isinstance(times, list) or not times:
        raise ClimateDataError("The climate archive returned no daily records.")

    if not isinstance(temperatures, list):
        temperatures = [None] * len(times)
    if not isinstance(precipitation, list):
        precipitation = [None] * len(times)

    buckets: dict[int, dict[str, float | int]] = {}
    for index, day in enumerate(times):
        try:
            year = int(str(day)[:4])
        except (TypeError, ValueError):
            continue
        if year < START_YEAR or year > END_YEAR:
            continue

        bucket = buckets.setdefault(
            year,
            {
                "temperature_sum": 0.0,
                "temperature_days": 0,
                "rainfall_sum": 0.0,
                "rainfall_days": 0,
            },
        )

        temperature = _valid_number(temperatures[index] if index < len(temperatures) else None)
        if temperature is not None:
            bucket["temperature_sum"] = float(bucket["temperature_sum"]) + temperature
            bucket["temperature_days"] = int(bucket["temperature_days"]) + 1

        rain = _valid_number(precipitation[index] if index < len(precipitation) else None)
        if rain is not None:
            bucket["rainfall_sum"] = float(bucket["rainfall_sum"]) + rain
            bucket["rainfall_days"] = int(bucket["rainfall_days"]) + 1

    temperature_series: list[dict[str, Any]] = []
    rainfall_series: list[dict[str, Any]] = []
    for year in sorted(buckets):
        bucket = buckets[year]
        temperature_days = int(bucket["temperature_days"])
        rainfall_days = int(bucket["rainfall_days"])

        if temperature_days >= MIN_VALID_DAYS:
            temperature_series.append(
                {
                    "year": year,
                    "value": round(float(bucket["temperature_sum"]) / temperature_days, 3),
                    "valid_days": temperature_days,
                }
            )
        if rainfall_days >= MIN_VALID_DAYS:
            rainfall_series.append(
                {
                    "year": year,
                    "value": round(float(bucket["rainfall_sum"]), 2),
                    "valid_days": rainfall_days,
                }
            )

    if not temperature_series and not rainfall_series:
        raise ClimateDataError("The climate archive returned no usable annual records.")

    return {"temperature": temperature_series, "rainfall": rainfall_series}


def _download_region(region: dict[str, Any]) -> dict[str, Any]:
    params = {
        "latitude": region["latitude"],
        "longitude": region["longitude"],
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }
    try:
        response = requests.get(
            ARCHIVE_URL,
            params=params,
            timeout=60,
            headers={"User-Agent": "ClimateTrendExplorer/1.0 (course project)"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ClimateDataError(
            "Could not download the climate record. Check the internet connection and try again."
        ) from exc

    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ClimateDataError("The climate archive returned an unexpected response.")

    series = _aggregate_annual(daily)
    return {
        "region": dict(region),
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": SOURCE,
        "series": series,
    }


def _read_cache(region_id: str) -> dict[str, Any] | None:
    path = _cache_path(region_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("series"), dict):
        return None
    return payload


def _write_cache(region_id: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(region_id)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=CACHE_DIR, delete=False, suffix=".tmp"
        ) as handle:
            json.dump(payload, handle, separators=(",", ":"))
            temporary = Path(handle.name)
        os.replace(temporary, path)
        os.chmod(path, 0o644)
    except OSError:
        # A cache write failure should not make a valid downloaded record fail.
        return


def load_region_series(region_id: str, force_refresh: bool = False) -> dict[str, Any]:
    """Load one region's annual series, downloading and caching it if needed."""

    if region_id not in REGIONS:
        raise ClimateInputError(f"Unknown region: {region_id!r}")

    if not force_refresh and region_id in _series_memory:
        return _series_memory[region_id]

    if not force_refresh:
        cached = _read_cache(region_id)
        if cached is not None:
            _series_memory[region_id] = cached
            return cached

    payload = _download_region(REGIONS[region_id])
    _write_cache(region_id, payload)
    _series_memory[region_id] = payload
    return payload


# ---------------------------------------------------------------------------
# Statistics


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes)."""

    max_iterations = 200
    epsilon = 3e-14
    tiny = 1e-300

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d

    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < epsilon:
            break

    return h


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    log_beta = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    beta = math.exp(log_beta)

    if x < (a + 1.0) / (a + b + 2.0):
        return beta * _betacf(a, b, x) / a
    return 1.0 - beta * _betacf(b, a, 1.0 - x) / b


def _student_t_two_sided_p(t_statistic: float, degrees_of_freedom: int) -> float:
    """Two-sided p-value for a t statistic, using the regularized beta."""

    if degrees_of_freedom <= 0:
        return 1.0
    if not math.isfinite(t_statistic):
        return 0.0 if abs(t_statistic) > 0 else 1.0
    x = degrees_of_freedom / (degrees_of_freedom + t_statistic * t_statistic)
    return min(1.0, max(0.0, _regularized_incomplete_beta(degrees_of_freedom / 2.0, 0.5, x)))


def _student_t_critical(degrees_of_freedom: int, confidence: float = 0.95) -> float:
    """Inverse two-sided t critical value (e.g. about 1.99 for df = 74)."""

    target = 1.0 - (1.0 - confidence) / 2.0
    low, high = 0.0, 40.0
    for _ in range(120):
        middle = (low + high) / 2.0
        cdf = 1.0 - _student_t_two_sided_p(middle, degrees_of_freedom) / 2.0
        if cdf < target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _newey_west_variance(x_values: list[float], residuals: list[float]) -> float:
    """HAC variance for the slope, with a small-sample correction.

    Annual climate values are serially correlated.  A plain OLS standard error
    would make trends look more certain than they are, so the reported p-value
    uses a Newey-West (Bartlett kernel) standard error instead.
    """

    n = len(x_values)
    mean_x = sum(x_values) / n
    centered = [value - mean_x for value in x_values]
    sxx = sum(value * value for value in centered)
    if sxx <= 0.0:
        return 0.0

    lag = max(1, int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0)))))
    weighted = [centered[index] * residuals[index] for index in range(n)]
    variance_sum = sum(value * value for value in weighted)

    for offset in range(1, lag + 1):
        weight = 1.0 - offset / (lag + 1.0)
        covariance = sum(
            weighted[index] * weighted[index - offset] for index in range(offset, n)
        )
        variance_sum += 2.0 * weight * covariance

    if variance_sum <= 0.0:
        return 0.0
    correction = n / max(1, n - 2)
    return correction * variance_sum / (sxx * sxx)


def calculate_trend(series: list[dict[str, Any]]) -> dict[str, Any]:
    """Fit a linear trend and test whether its slope differs from zero."""

    points = sorted(series, key=lambda point: point["year"])
    n = len(points)
    if n < MIN_TREND_YEARS:
        raise ClimateDataError(
            f"Not enough annual records for a reliable trend test (found {n}, need {MIN_TREND_YEARS})."
        )

    x_values = [float(point["year"]) for point in points]
    y_values = [float(point["value"]) for point in points]

    mean_x = sum(x_values) / n
    mean_y = sum(y_values) / n
    sxx = sum((value - mean_x) ** 2 for value in x_values)
    sxy = sum((x_values[index] - mean_x) * (y_values[index] - mean_y) for index in range(n))
    if sxx <= 0.0:
        raise ClimateDataError("The annual records do not span a usable time range.")

    slope = sxy / sxx
    intercept = mean_y - slope * mean_x

    residuals = [
        y_values[index] - (intercept + slope * x_values[index]) for index in range(n)
    ]
    sse = sum(value * value for value in residuals)
    sst = sum((value - mean_y) ** 2 for value in y_values)
    degrees_of_freedom = n - 2

    classical_variance = (sse / degrees_of_freedom) / sxx if degrees_of_freedom > 0 else 0.0
    variance = _newey_west_variance(x_values, residuals)
    method = "ordinary least squares with Newey-West HAC standard errors"
    if variance <= 0.0:
        # Degenerate HAC estimate (for example a perfectly flat series): fall
        # back to the classical OLS standard error rather than reporting zero.
        variance = classical_variance
        method = "ordinary least squares with classical standard errors"
    standard_error = math.sqrt(max(variance, 0.0))

    if standard_error <= 0.0:
        t_statistic = 0.0 if abs(slope) < 1e-15 else math.copysign(float("inf"), slope)
        p_value = 1.0 if t_statistic == 0.0 else 0.0
    else:
        t_statistic = slope / standard_error
        p_value = _student_t_two_sided_p(t_statistic, degrees_of_freedom)

    t_critical = _student_t_critical(degrees_of_freedom)
    ci_low = slope - t_critical * standard_error
    ci_high = slope + t_critical * standard_error

    r_squared = 0.0
    if sst > 0.0:
        r_squared = max(0.0, min(1.0, 1.0 - sse / sst))

    residual_std_dev = math.sqrt(sse / degrees_of_freedom) if degrees_of_freedom > 0 else 0.0
    years_span = max(x_values) - min(x_values)

    return {
        "slope_per_year": slope,
        "change_per_decade": slope * 10.0,
        "change_over_record": slope * years_span,
        "intercept": intercept,
        "standard_error_per_year": standard_error,
        "ci95_per_decade": {"low": ci_low * 10.0, "high": ci_high * 10.0},
        "t_statistic": t_statistic,
        "degrees_of_freedom": degrees_of_freedom,
        "p_value": p_value,
        "r_squared": r_squared,
        "residual_std_dev": residual_std_dev,
        "significant": p_value < ALPHA,
        "alpha": ALPHA,
        "hac_lag": max(1, int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))),
        "method": method,
    }


def _signed(value: float, digits: int) -> str:
    if abs(value) < 0.5 * (10 ** -digits):
        return f"{0:.{digits}f}"
    sign = "−" if value < 0 else "+"
    return f"{sign}{abs(value):.{digits}f}"


def _format_p(p_value: float) -> str:
    if p_value < 0.001:
        return "p < 0.001"
    if p_value > 0.999:
        return "p > 0.999"
    return f"p = {p_value:.3f}"


def _interpretation(
    region: dict[str, Any],
    measure: dict[str, Any],
    trend: dict[str, Any],
    start_year: int,
    end_year: int,
) -> dict[str, str]:
    rate = trend["change_per_decade"]
    unit = measure["unit"]
    direction = "increase" if rate > 0 else "decrease" if rate < 0 else "change"
    significant = trend["significant"]
    p_text = _format_p(trend["p_value"])
    ci_low = trend["ci95_per_decade"]["low"]
    ci_high = trend["ci95_per_decade"]["high"]
    rate_digits = 2 if measure["id"] == "temperature" else 1

    if significant:
        headline = f"Statistically significant {direction}"
        test_sentence = (
            f"The test gives {p_text}. Because that is below the 0.05 threshold, "
            "the trend is statistically significant: a slope at least this steep "
            "would be unlikely if the region had no underlying trend and the years "
            "varied only randomly."
        )
    else:
        headline = "No statistically significant trend"
        test_sentence = (
            f"The test gives {p_text}. Because that is above the 0.05 threshold, "
            "the trend is not statistically significant. An apparent change this "
            "size could plausibly arise from normal year-to-year variation; this "
            "does not prove there is no trend, only that this record cannot "
            "distinguish it from noise."
        )

    summary = (
        f"The fitted trend for {region_display(region)} is "
        f"{_signed(rate, rate_digits)} {unit} per decade "
        f"(95% confidence interval {_signed(ci_low, rate_digits)} to "
        f"{_signed(ci_high, rate_digits)}). Across {start_year}–{end_year} "
        f"that implies a total fitted {direction} of "
        f"{_signed(trend['change_over_record'], 1)} {unit}."
    )

    caveat = (
        "This analysis uses one ERA5 grid cell, not a full regional average. "
        "The test asks whether a straight-line trend is distinguishable from "
        "year-to-year noise in this particular record; it does not establish "
        "cause, and a different period or measure can give a different answer. "
        "Newey–West standard errors account for correlation between consecutive "
        "years, but the result still depends on the chosen record length."
    )

    return {
        "headline": headline,
        "summary": summary,
        "test": test_sentence,
        "caveat": caveat,
    }


def build_trend(region_id: str, measure_id: str) -> dict[str, Any]:
    """Build the complete response for one region/measure combination."""

    if measure_id not in MEASURES:
        raise ClimateInputError(f"Unknown measure: {measure_id!r}")

    region = REGIONS.get(region_id)
    if region is None:
        raise ClimateInputError(f"Unknown region: {region_id!r}")

    payload = load_region_series(region_id)
    measure = MEASURES[measure_id]
    series = payload.get("series", {}).get(measure_id)
    if not isinstance(series, list) or len(series) < MIN_TREND_YEARS:
        raise ClimateDataError(
            f"Not enough usable {measure['label'].lower()} records for this region."
        )

    trend = calculate_trend(series)
    start_year = int(series[0]["year"])
    end_year = int(series[-1]["year"])
    interpretation = _interpretation(region, measure, trend, start_year, end_year)

    return {
        "region": {
            "id": region["id"],
            "name": region["name"],
            "country": region["country"],
            "display": region_display(region),
            "latitude": region["latitude"],
            "longitude": region["longitude"],
        },
        "measure": {
            "id": measure["id"],
            "label": measure["label"],
            "short_label": measure["short_label"],
            "unit": measure["unit"],
            "decade_unit": measure["decade_unit"],
            "chart_label": measure["chart_label"],
            "description": measure["description"],
        },
        "period": {
            "start_year": start_year,
            "end_year": end_year,
            "years": len(series),
        },
        "series": series,
        "trend": trend,
        "interpretation": interpretation,
        "source": payload.get("source", SOURCE),
        "fetched_at": payload.get("fetched_at"),
    }
