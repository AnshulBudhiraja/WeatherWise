import json
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_LABELS = {
    0: ("Clear", "☀️"), 1: ("Mostly clear", "🌤️"), 2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"), 45: ("Foggy", "🌫️"), 48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Heavy drizzle", "🌧️"),
    56: ("Freezing drizzle", "🌧️"), 57: ("Freezing drizzle", "🌧️"),
    61: ("Light rain", "🌦️"), 63: ("Rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"), 67: ("Freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨️"), 80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"), 82: ("Heavy showers", "⛈️"),
    85: ("Snow showers", "🌨️"), 86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorms", "⛈️"), 96: ("Storms with hail", "⛈️"),
    99: ("Severe storms with hail", "⛈️"),
}


class ServiceError(Exception):
    pass


def _get_json(url, params):
    request = Request(f"{url}?{urlencode(params, doseq=True)}", headers={"User-Agent": "Weatherwise/1.0"})
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ServiceError("The weather service is unavailable right now. Please try again shortly.") from exc


def validate_trip(data):
    city = str(data.get("city", "")).strip()
    country = str(data.get("country", "")).strip()
    persona = str(data.get("persona", "")).strip()
    if not city or not country or persona not in {"explorer", "trekker", "event", "family"}:
        raise ValueError("Please complete the city, country and traveller fields.")
    try:
        start = date.fromisoformat(str(data.get("start_date", "")))
        end = date.fromisoformat(str(data.get("end_date", "")))
    except ValueError as exc:
        raise ValueError("Please choose valid travel dates.") from exc
    today = date.today()
    if start < today:
        raise ValueError("The start date cannot be in the past.")
    if end < start:
        raise ValueError("The end date must be on or after the start date.")
    if end > today + timedelta(days=14):
        raise ValueError("Forecasts are available only up to 14 days ahead.")
    return city, country, persona, start, end


def search_locations(city, country):
    payload = _get_json(GEOCODING_URL, {"name": city, "count": 10, "language": "en", "format": "json"})
    results = payload.get("results") or []
    country_key = country.casefold()
    matches = [r for r in results if country_key in str(r.get("country", "")).casefold() or country_key == str(r.get("country_code", "")).casefold()]
    if not matches:
        return []
    exact = [r for r in matches if str(r.get("name", "")).casefold() == city.casefold()]
    return exact or matches


def location_payload(item):
    return {
        "name": item.get("name"), "admin1": item.get("admin1") or "",
        "country": item.get("country"), "country_code": item.get("country_code") or "",
        "latitude": item.get("latitude"), "longitude": item.get("longitude"),
        "timezone": item.get("timezone") or "auto",
    }


def fetch_forecast(latitude, longitude, start, end):
    daily_fields = [
        "weather_code", "temperature_2m_max", "temperature_2m_min",
        "apparent_temperature_max", "apparent_temperature_min",
        "precipitation_probability_max", "precipitation_sum", "uv_index_max",
        "wind_speed_10m_max", "sunrise", "sunset",
    ]
    return _get_json(FORECAST_URL, {
        "latitude": latitude, "longitude": longitude, "daily": ",".join(daily_fields),
        "timezone": "auto", "start_date": start.isoformat(), "end_date": end.isoformat(),
    })


def _number(values, index, fallback=0):
    try:
        value = values[index]
        return fallback if value is None else value
    except (IndexError, TypeError):
        return fallback


def day_verdict(day, persona):
    rain = day["rain_probability"]
    wind = day["wind"]
    uv = day["uv"]
    high = day["high"]
    code = day["weather_code"]
    if code >= 95:
        return "Storms could disrupt plans - keep a flexible indoor backup.", "rough"
    if rain >= 70 or day["precipitation"] >= 10:
        return "A properly wet day - plan indoor time and waterproof everything.", "rough"
    if persona == "trekker" and wind >= 35:
        return "Exposed trails may feel unsafe in strong gusts - choose a sheltered route.", "rough"
    if persona == "family" and (high >= 34 or uv >= 8):
        return "Keep outdoor time short around midday and plan cool, shaded breaks.", "mixed"
    if persona == "event" and rain >= 35:
        return "Outdoor plans are possible, but keep a covered venue option ready.", "mixed"
    if rain >= 40:
        return "Mostly workable with passing rain - carry a compact umbrella.", "mixed"
    if high >= 36:
        return "Very hot - shift plans to morning or evening and hydrate often.", "mixed"
    if high <= 8:
        return "Cold enough to shape the day - layer up before heading out.", "mixed"
    if uv >= 7:
        return "Good outside, with strong sun - seek shade around midday.", "good"
    if wind >= 30:
        return "Pleasant enough, though breezy - secure loose layers and plans.", "mixed"
    return "A comfortable, unremarkable day for flexible outdoor plans.", "good"


def packing_list(days, persona):
    items = {"Comfortable walking shoes", "Reusable water bottle", "Light everyday layers"}
    if any(d["rain_probability"] >= 35 or d["precipitation"] >= 2 for d in days):
        items.update({"Compact umbrella", "Light rain jacket"})
    if any(d["uv"] >= 5 or d["high"] >= 28 for d in days):
        items.update({"Sunscreen", "Sunglasses or a sun hat"})
    if any(d["low"] <= 12 for d in days):
        items.add("Warm layer for cool hours")
    if any(d["wind"] >= 30 for d in days):
        items.add("Wind-resistant outer layer")
    persona_items = {
        "trekker": {"Trail-ready footwear", "Small first-aid kit"},
        "event": {"Weather-safe shoe option", "Garment cover"},
        "family": {"Child-safe sunscreen", "Spare toddler outfit", "Snacks"},
        "explorer": {"Day bag", "Portable charger"},
    }
    items.update(persona_items[persona])
    return sorted(items)


def shape_forecast(payload, persona):
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        raise ServiceError("No forecast was returned for those dates.")
    days = []
    for index, iso_date in enumerate(dates):
        code = int(_number(daily.get("weather_code"), index))
        label, icon = WEATHER_LABELS.get(code, ("Changeable", "🌤️"))
        day = {
            "date": iso_date, "weather_code": code, "condition": label, "icon": icon,
            "high": round(_number(daily.get("temperature_2m_max"), index), 1),
            "low": round(_number(daily.get("temperature_2m_min"), index), 1),
            "feels_high": round(_number(daily.get("apparent_temperature_max"), index), 1),
            "rain_probability": round(_number(daily.get("precipitation_probability_max"), index)),
            "precipitation": round(_number(daily.get("precipitation_sum"), index), 1),
            "uv": round(_number(daily.get("uv_index_max"), index), 1),
            "wind": round(_number(daily.get("wind_speed_10m_max"), index), 1),
            "sunrise": str(_number(daily.get("sunrise"), index, ""))[-5:],
            "sunset": str(_number(daily.get("sunset"), index, ""))[-5:],
        }
        day["verdict"], day["rating"] = day_verdict(day, persona)
        days.append(day)
    rough = sum(d["rating"] == "rough" for d in days)
    mixed = sum(d["rating"] == "mixed" for d in days)
    if rough:
        summary = f"A changeable trip: {rough} day{'s' if rough != 1 else ''} need a solid backup plan."
        tone = "rough"
    elif mixed:
        summary = f"A promising trip with {mixed} day{'s' if mixed != 1 else ''} worth planning around."
        tone = "mixed"
    else:
        summary = "The forecast looks easygoing - most plans should work as they are."
        tone = "good"
    return days, summary, tone, packing_list(days, persona)
