from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src import WeatherDatabaseApi, WeatherAPI
from dotenv import load_dotenv
import os
from cachetools import TTLCache
import logging
import time
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create caches with longer TTL for testing
weather_cache = TTLCache(maxsize=10000, ttl=7200)  # 2 hour cache
forecast_cache = TTLCache(maxsize=10000, ttl=7200)

# Create FastAPI app
app = FastAPI()

# Rate limiting settings
RATE_LIMIT = 60  # requests per minute
rate_limit_dict = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_rate_limit(ip: str) -> bool:
    """Simple rate limiting implementation"""
    current_time = time.time()
    if ip in rate_limit_dict:
        request_times = rate_limit_dict[ip]
        # Remove old requests
        request_times = [t for t in request_times if current_time - t < 60]
        if len(request_times) >= RATE_LIMIT:
            return False
        request_times.append(current_time)
        rate_limit_dict[ip] = request_times
    else:
        rate_limit_dict[ip] = [current_time]
    return True


def initialize_api():
    """Initialize WeatherAPI with validation."""
    api_access_key = os.environ.get("WEATHER_API_ACCESS_TOKEN")
    if not api_access_key:
        logger.error("No API key found in environment variables")
        raise HTTPException(status_code=500, detail="Weather API key not configured")
    return WeatherAPI(api_access_key)


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/get_weather/{city}")
async def get_weather(city: str):
    """API endpoint for current weather with enhanced error handling."""
    logger.debug(f"Weather request for city: {city}")

    # Check cache first
    cache_key = f"weather:{city}"
    if cache_key in weather_cache:
        logger.debug(f"Cache hit for {city}")
        return weather_cache[cache_key]

    try:
        weather_api = initialize_api()
        current = weather_api.get_current_weather(city)

        if not current:
            raise HTTPException(
                status_code=404, detail=f"No weather data found for {city}"
            )

        response = {
            "current_Temp": round(current.get("temperature", 0), 1),
            "feels_like_temp": round(current.get("feels_like", 0), 1),
            "humidity": round(current.get("humidity", 0), 1),
            "wind_speed": round(current.get("wind_speed", 0), 1),
            "description": current.get("description", "N/A"),
            "main_description": current.get("main_description", "N/A"),
        }

        # Cache the successful response
        weather_cache[cache_key] = response
        return response

    except Exception as e:
        logger.error(f"Error fetching weather for {city}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_forecast/{city}")
async def get_forecast(city: str):
    """API endpoint for forecast with enhanced error handling."""
    logger.debug(f"Forecast request for city: {city}")

    # Check cache first
    cache_key = f"forecast:{city}"
    if cache_key in forecast_cache:
        logger.debug(f"Cache hit for {city} forecast")
        return forecast_cache[cache_key]

    try:
        weather_api = initialize_api()
        forecast_data = weather_api.get_forecast(city)

        if not forecast_data:
            raise HTTPException(
                status_code=404, detail=f"No forecast data found for {city}"
            )

        # Cache the successful response
        forecast_cache[cache_key] = forecast_data
        return forecast_data

    except Exception as e:
        logger.error(f"Error fetching forecast for {city}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_cities")
async def get_cities():
    """API endpoint to get available cities with enhanced error handling."""
    try:
        weather_db = WeatherDatabaseApi("data/db/application", deploy_database=False)
        city_data = weather_db.get_active_states()
        cities = [details["city"] for location, details in city_data.items()]

        if not cities:
            raise HTTPException(status_code=404, detail="No cities found in database")

        return {"cities": cities}

    except Exception as e:
        logger.error(f"Error fetching cities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware to log all requests"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.debug(f"{request.method} {request.url.path} completed in {duration:.2f}s")
    return response
