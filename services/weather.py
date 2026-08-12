import os
from typing import Optional

import httpx

WEATHER_API_URL = os.getenv(
    "WEATHER_API_URL",
    "https://api.open-meteo.com/v1/forecast",
)

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def get_coordinates(city: str, country: str = "Kenya") -> Optional[tuple]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                GEOCODING_API_URL,
                params={
                    "name": city,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
                timeout=10,
            )

            response.raise_for_status()

            data = response.json()

            if data.get("results"):
                result = data["results"][0]
                return result["latitude"], result["longitude"]

        except Exception as e:
            print(f"Geocoding error: {e}")

    return None


async def get_weather(city: str, country: str = "Kenya"):

    coordinates = await get_coordinates(city, country)

    if not coordinates:
        return None

    lat, lon = coordinates

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                WEATHER_API_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "timezone": "Africa/Nairobi",
                },
                timeout=10,
            )

            response.raise_for_status()

            data = response.json()

            return data.get("current_weather")

        except Exception as e:
            print(f"Weather error: {e}")

    return None