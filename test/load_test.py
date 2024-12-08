from locust import HttpUser, task, between
import json
import random


class WeatherAppUser(HttpUser):
    wait_time = between(1, 3)
    cities = None

    def on_start(self):
        """Initialize session and get available cities"""
        # Get list of cities
        response = self.client.get("/get_cities")
        if response.status_code == 200:
            self.cities = response.json()["cities"]
        else:
            # Fallback cities if API call fails
            self.cities = ["Durham", "New York", "Los Angeles", "Chicago", "Houston"]

    @task(2)
    def test_weather_api(self):
        """Test the weather API endpoint"""
        if self.cities:
            city = random.choice(self.cities)
            with self.client.get(
                f"/get_weather/{city}", catch_response=True
            ) as response:
                try:
                    if response.status_code == 200:
                        data = response.json()
                        if "current_Temp" in data:
                            response.success()
                        else:
                            response.failure("Missing temperature data")
                    else:
                        response.failure(f"Status code: {response.status_code}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")

    @task(1)
    def test_forecast_api(self):
        """Test the forecast API endpoint"""
        if self.cities:
            city = random.choice(self.cities)
            with self.client.get(
                f"/get_forecast/{city}", catch_response=True
            ) as response:
                try:
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            response.success()
                        else:
                            response.failure("Invalid forecast data format")
                    else:
                        response.failure(f"Status code: {response.status_code}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
