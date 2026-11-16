# Climate data cache

Each JSON file holds annual aggregates for one study region:

- `temperature` — annual mean of daily mean temperature, °C.
- `rainfall` — annual total precipitation, mm.

Source: ERA5 reanalysis through the
[Open-Meteo Archive API](https://open-meteo.com/en/docs/historical-weather-api).
Years with fewer than 330 valid days are omitted. The record runs from 1950
through 2025.

`UI/climate.py` creates these files automatically. Delete a file (or run with
`CLIMATE_CACHE_DIR` pointing at a different directory) to force a fresh
download. No API key is required.
