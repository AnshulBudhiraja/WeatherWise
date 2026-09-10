# Weatherwise

A responsive Django weather planner that turns live Open-Meteo forecasts into trip decisions. The UI includes the four required states (welcome, loading, error, results), asks for city, country, dates and traveller persona, handles ambiguous city names explicitly, and produces daily verdicts plus one deduplicated packing list.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py runserver
```

Open http://127.0.0.1:8000/.

## Runtime flow

1. The browser posts the trip inputs to Django.
2. Django validates the dates (today through 14 days ahead).
3. Django searches Open-Meteo Geocoding and filters results by country.
4. If a city remains ambiguous, the user chooses the intended region; no first result is silently selected.
5. Django sends the selected latitude and longitude to Open-Meteo Forecast.
6. A small rules engine prioritizes storms/rain, heat, UV and wind, adjusts advice for the selected persona, and returns one verdict per day, an overall summary and one packing list.

## Decision thresholds

- Thunderstorm weather codes, rain probability of 70%+, or precipitation of 10 mm+ make a day rough.
- 40%+ rain, 36°C+ heat, strong wind, or persona-specific exposure concerns make a day mixed.
- UV 7+ keeps a day good but adds a midday shade warning.
- An ordinary day is described plainly rather than overstated.

Hourly detail is deliberately omitted: the product is for fast trip decisions, not meteorological analysis. Next steps would be saved/shareable trips, accessible unit preferences and push alerts when the forecast changes materially.

## Deployment

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS=your-domain`, run `python manage.py collectstatic --noinput`, and start with `gunicorn weatherwise.wsgi`.

For Render, the included `render.yaml` supplies the build/start commands and generates the secret automatically. Create a new Blueprint from this repository, then replace or extend `DJANGO_ALLOWED_HOSTS` if you attach a custom domain.
