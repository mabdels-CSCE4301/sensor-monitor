from datetime import date, timedelta

import pytest

import climate
from app import app


def synthetic_series(points):
    return [{"year": 1950 + index, "value": value, "valid_days": 365} for index, value in enumerate(points)]


def fake_region_payload(series):
    return {
        "series": series,
        "source": climate.SOURCE,
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


def temperature_points():
    # A clear upward trend with a repeating wobble, long enough for the test.
    import math

    return [10.0 + 0.03 * index + 0.4 * math.sin(index) for index in range(76)]


def test_student_t_p_values_match_reference_values():
    assert climate._student_t_two_sided_p(0.0, 74) == pytest.approx(1.0)
    assert climate._student_t_two_sided_p(2.0, 74) == pytest.approx(0.0491706, rel=1e-5)
    assert climate._student_t_two_sided_p(2.0, 10) == pytest.approx(0.0733880, rel=1e-5)
    assert climate._student_t_two_sided_p(10.0, 10) < 1e-5


def test_t_critical_values_are_two_sided():
    assert climate._student_t_critical(74) == pytest.approx(1.9925, rel=1e-3)
    assert climate._student_t_critical(10) == pytest.approx(2.2281, rel=1e-3)


def test_calculate_trend_finds_significant_warming():
    trend = climate.calculate_trend(synthetic_series(temperature_points()))

    assert trend["change_per_decade"] == pytest.approx(0.03 * 10, abs=0.02)
    assert trend["significant"] is True
    assert trend["p_value"] < 0.05
    assert trend["ci95_per_decade"]["low"] > 0
    assert trend["ci95_per_decade"]["high"] > trend["ci95_per_decade"]["low"]
    assert trend["r_squared"] > 0.5


def test_calculate_trend_does_not_call_noise_significant():
    points = [10.0 + (0.5 if index % 2 else -0.5) for index in range(76)]
    trend = climate.calculate_trend(synthetic_series(points))

    assert trend["significant"] is False
    assert trend["p_value"] > 0.05
    assert trend["ci95_per_decade"]["low"] < 0 < trend["ci95_per_decade"]["high"]


def test_calculate_trend_rejects_short_records():
    with pytest.raises(climate.ClimateDataError):
        climate.calculate_trend(synthetic_series([1.0] * 10))


def test_aggregate_annual_means_temperature_and_sums_rainfall():
    start = date(2001, 1, 1)
    times = [(start + timedelta(days=index)).isoformat() for index in range(365)]
    temperatures = [10.0] * 365
    precipitation = [1.25] * 365
    temperatures[0] = None
    precipitation[0] = None

    series = climate._aggregate_annual(
        {
            "time": times,
            "temperature_2m_mean": temperatures,
            "precipitation_sum": precipitation,
        }
    )

    assert series["temperature"] == [{"year": 2001, "value": 10.0, "valid_days": 364}]
    assert series["rainfall"] == [{"year": 2001, "value": 455.0, "valid_days": 364}]


def test_aggregate_annual_skips_incomplete_years():
    complete_start = date(2002, 1, 1)
    partial_start = date(2003, 1, 1)
    times = [
        *[(complete_start + timedelta(days=index)).isoformat() for index in range(365)],
        *[(partial_start + timedelta(days=index)).isoformat() for index in range(100)],
    ]
    values = [12.0] * 365 + [99.0] * 100
    rain = [2.0] * 365 + [99.0] * 100

    series = climate._aggregate_annual(
        {
            "time": times,
            "temperature_2m_mean": values,
            "precipitation_sum": rain,
        }
    )

    assert series["temperature"] == [{"year": 2002, "value": 12.0, "valid_days": 365}]
    assert series["rainfall"] == [{"year": 2002, "value": 730.0, "valid_days": 365}]


def test_build_trend_combines_metadata_and_interpretation(monkeypatch):
    payload = fake_region_payload(
        {
            "temperature": synthetic_series(temperature_points()),
            "rainfall": synthetic_series([600.0 + (index % 3) for index in range(76)]),
        }
    )
    monkeypatch.setattr(climate, "load_region_series", lambda region_id: payload)

    data = climate.build_trend("london", "temperature")

    assert data["region"]["display"] == "London, United Kingdom"
    assert data["measure"]["unit"] == "°C"
    assert data["period"]["years"] == 76
    assert data["trend"]["significant"] is True
    assert "p < 0.001" in data["interpretation"]["test"]
    assert "fitted trend for London, United Kingdom" in data["interpretation"]["summary"]


def test_build_trend_rejects_unknown_inputs():
    with pytest.raises(climate.ClimateInputError):
        climate.build_trend("atlantis", "temperature")
    with pytest.raises(climate.ClimateInputError):
        climate.build_trend("london", "wind")


def test_flask_climate_routes_serve_page_options_and_trend(monkeypatch):
    client = app.test_client()

    page = client.get("/climate")
    assert page.status_code == 200
    assert 'id="measure-select"' in page.get_data(as_text=True)
    assert "/static/climate.js" in page.get_data(as_text=True)

    options = client.get("/api/climate/options")
    assert options.status_code == 200
    body = options.get_json()
    assert {measure["id"] for measure in body["measures"]} == {"temperature", "rainfall"}
    assert any(region["id"] == "london" for region in body["regions"])

    payload = fake_region_payload(
        {
            "temperature": synthetic_series(temperature_points()),
            "rainfall": synthetic_series([600.0 + (index % 3) for index in range(76)]),
        }
    )
    monkeypatch.setattr(climate, "load_region_series", lambda region_id: payload)

    trend = client.get("/api/climate/trend?region=london&measure=temperature")
    assert trend.status_code == 200
    assert trend.get_json()["trend"]["significant"] is True

    missing = client.get("/api/climate/trend?region=atlantis&measure=temperature")
    assert missing.status_code == 400
    assert missing.get_json()["success"] is False
