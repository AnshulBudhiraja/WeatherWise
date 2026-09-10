import json
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase


class PlannerTests(TestCase):
    def payload(self):
        today = date.today()
        return {
            "city": "Jaipur", "country": "India", "persona": "explorer",
            "start_date": today.isoformat(), "end_date": (today + timedelta(days=1)).isoformat(),
        }

    def test_home_has_all_four_states(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for state_id in (b'welcomeState', b'loadingState', b'errorState', b'resultsState'):
            self.assertContains(response, state_id)

    def test_rejects_dates_beyond_forecast_window(self):
        data = self.payload()
        data["end_date"] = (date.today() + timedelta(days=15)).isoformat()
        response = self.client.post("/api/plan/", json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("planner.views.fetch_forecast")
    @patch("planner.views.search_locations")
    def test_returns_interpreted_forecast(self, search, forecast):
        search.return_value = [{"name": "Jaipur", "country": "India", "admin1": "Rajasthan", "latitude": 26.91, "longitude": 75.79}]
        today = date.today()
        forecast.return_value = {"timezone": "Asia/Kolkata", "daily": {
            "time": [today.isoformat(), (today + timedelta(days=1)).isoformat()],
            "weather_code": [0, 65], "temperature_2m_max": [29, 27], "temperature_2m_min": [18, 19],
            "apparent_temperature_max": [30, 28], "apparent_temperature_min": [18, 20],
            "precipitation_probability_max": [5, 90], "precipitation_sum": [0, 15],
            "uv_index_max": [6, 3], "wind_speed_10m_max": [12, 18],
            "sunrise": [f"{today.isoformat()}T06:10", f"{today.isoformat()}T06:11"],
            "sunset": [f"{today.isoformat()}T18:30", f"{today.isoformat()}T18:29"],
        }}
        response = self.client.post("/api/plan/", json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result["days"]), 2)
        self.assertEqual(result["tone"], "rough")
        self.assertIn("Light rain jacket", result["packing"])

    @patch("planner.views.search_locations")
    def test_ambiguous_city_requires_selection(self, search):
        search.return_value = [
            {"name": "Springfield", "country": "United States", "admin1": "Illinois", "latitude": 1, "longitude": 2},
            {"name": "Springfield", "country": "United States", "admin1": "Missouri", "latitude": 3, "longitude": 4},
        ]
        data = self.payload() | {"city": "Springfield", "country": "United States"}
        response = self.client.post("/api/plan/", json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.json()["needs_selection"])
