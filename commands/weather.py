import logging
import re
import requests

from config import DEFAULT_CITY, WEATHER_API_KEY, WEATHER_API_URL

logger = logging.getLogger(__name__)
API_KEY = WEATHER_API_KEY
URL = WEATHER_API_URL


def extract_city(command):
    """Extract city from user command. Defaults to Thane if none is found."""
    command = command.lower()

    patterns = [
        r"weather in (.+)",
        r"weather of (.+)",
        r"temperature in (.+)",
        r"forecast in (.+)",
        r"forecast for (.+)",
        r"in (.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            city = match.group(1)
            city = city.replace("?", "")
            city = city.replace(".", "")
            city = city.strip()
            return city.title()

    return DEFAULT_CITY


def get_weather(command):
    """Fetch and announce weather for the given command."""
    if not API_KEY:
        logger.error("Weather lookup requested but WEATHER_API_KEY is not configured")
        return "Weather API key is missing."

    city = extract_city(command)

    params = {
        "key": API_KEY,
        "q": city,
        "days": 1,
        "aqi": "no",
        "alerts": "no"
    }

    try:
        response = requests.get(URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or "error" in data:
            logger.info("Weather service returned no result for city %s", city)
            return f"Sorry, I couldn't find weather information for {city}."

        location = data["location"]
        current = data["current"]
        forecast = data["forecast"]["forecastday"][0]["day"]

        temperature = current["temp_c"]
        feels_like = current["feelslike_c"]
        rain_chance = int(forecast["daily_chance_of_rain"])

        # Rain advice
        if rain_chance >= 70:
            rain_message = "There is a high chance of rain today. Carry an umbrella."
        elif rain_chance >= 40:
            rain_message = "There is a moderate chance of rain today."
        else:
            rain_message = "Rain is unlikely today."

        # Temperature advice
        if temperature >= 38:
            temp_message = "It is extremely hot outside. Stay hydrated."
        elif temperature <= 15:
            temp_message = "It is quite cold today. Consider wearing a jacket."
        else:
            temp_message = ""

        message = (
            f"The temperature in {location['name']} is "
            f"{temperature} degrees Celsius. "
            f"It feels like {feels_like} degrees. "
            f"The chance of rain today is {rain_chance} percent. "
            f"{rain_message} {temp_message}"
        )

        return message

    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        logger.exception("Could not fetch or parse weather for %s", city)
        return "Sorry, I couldn't fetch the weather right now."