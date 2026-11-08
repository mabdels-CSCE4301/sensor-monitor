import os
from typing import Any

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

API_KEY = os.getenv("OPENWEATHER_API_KEY")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> dict[str, Any]:
    if not city or not city.strip():
        raise ValueError("Please enter a city name.")

    if not API_KEY:
        raise RuntimeError("Missing OPENWEATHER_API_KEY environment variable.")

    response = requests.get(
        WEATHER_URL,
        params={
            "q": city,
            "appid": API_KEY,
            "units": "metric",
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError(f"Could not find weather for '{city}'.")

    data = response.json()
    weather = data.get("weather", [{}])[0]
    main = data.get("main", {})
    sys_data = data.get("sys", {})

    return {
        "city": data.get("name", city),
        "country": sys_data.get("country", ""),
        "temperature": main.get("temp"),
        "description": weather.get("description", "No description available"),
        "humidity": main.get("humidity"),
        "icon": weather.get("icon", "01d"),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        if city:
            try:
                weather = get_weather(city)
                weather["icon_url"] = f"https://openweathermap.org/img/wn/{weather['icon']}@2x.png"
            except (RuntimeError, ValueError) as exc:
                error = str(exc)
        else:
            error = "Please enter a city name."

    return render_template("index.html", weather=weather, error=error)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
