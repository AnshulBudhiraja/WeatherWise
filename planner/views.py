import json
from datetime import date, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services import ServiceError, fetch_forecast, location_payload, search_locations, shape_forecast, validate_trip


def home(request):
    today = date.today()
    return render(request, "planner/index.html", {
        "today": today.isoformat(), "max_date": (today + timedelta(days=14)).isoformat()
    })


@require_POST
def plan_trip(request):
    try:
        data = json.loads(request.body or "{}")
        city, country, persona, start, end = validate_trip(data)
        chosen = data.get("chosen_location")
        if chosen:
            try:
                latitude = float(chosen["latitude"])
                longitude = float(chosen["longitude"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("That location selection was invalid. Please search again.") from exc
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("That location selection was invalid. Please search again.")
            location = {
                "name": str(chosen.get("name", city)), "admin1": str(chosen.get("admin1", "")),
                "country": str(chosen.get("country", country)), "latitude": latitude, "longitude": longitude,
            }
        else:
            matches = search_locations(city, country)
            if not matches:
                return JsonResponse({"error": "We could not find that city in the selected country. Check the spelling and try again."}, status=404)
            locations = [location_payload(match) for match in matches]
            if len(locations) > 1:
                return JsonResponse({"needs_selection": True, "locations": locations}, status=409)
            location = locations[0]
            latitude, longitude = location["latitude"], location["longitude"]
        forecast = fetch_forecast(latitude, longitude, start, end)
        days, summary, tone, packing = shape_forecast(forecast, persona)
        return JsonResponse({
            "location": location, "days": days, "summary": summary,
            "tone": tone, "packing": packing, "timezone": forecast.get("timezone", "Local time"),
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "The request could not be read. Please try again."}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
