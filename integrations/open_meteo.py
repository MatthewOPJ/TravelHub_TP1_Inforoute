import unicodedata
import requests
from .exceptions import ExternalServiceError, LocationNotFound, NoDataAvailable
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
# en secondes
TIMEOUT = 8
# Codes météo WMO utilisés par Open-Meteo
WEATHER_CODES = {
    0: "Ciel dégagé",
    1: "Plutôt dégagé",
    2: "Partiellement nuageux",
    3: "Couvert",
    45: "Brouillard",
    48: "Brouillard givrant",
    51: "Bruine légère",
    53: "Bruine modérée",
    55: "Bruine forte",
    56: "Bruine verglaçante légère",
    57: "Bruine verglaçante forte",
    61: "Pluie faible",
    63: "Pluie modérée",
    65: "Pluie forte",
    66: "Pluie verglaçante légère",
    67: "Pluie verglaçante forte",
    71: "Neige faible",
    73: "Neige modérée",
    75: "Neige forte",
    77: "Grains de neige",
    80: "Averses faibles",
    81: "Averses modérées",
    82: "Averses violentes",
    85: "Averses de neige faibles",
    86: "Averses de neige fortes",
    95: "Orage",
    96: "Orage avec grêle légère",
    99: "Orage avec forte grêle",
}


def get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise ExternalServiceError("Open-Meteo n'a pas répondu à temps.") from exc
    except requests.RequestException as exc:
        raise ExternalServiceError("Open-Meteo est inaccessible ou a renvoyé une erreur.") from exc
    
def normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    # TODO: WTF, man, ya un moyen plus simple de faire ca cest sur...
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()

# retourne la localisation d'une ville
def get_geocode(city, country=None):
    data = get_json(
        GEOCODING_URL,
        {"name": city, "count": 10, "language": "fr", "format": "json"},
    )
    
    results = data.get("results")
    
    if not results or len(results) == 0:
        raise LocationNotFound(f"Aucune localisation trouvée pour « {city} ».")
    
    chosen = results[0]
    if country:
        wanted = normalize(country)
    for item in results:
        if wanted in (normalize(item.get("country")), normalize(item.get("country_code"))):
            chosen = item
            break
        
    return {
        "name": chosen.get("name"),
        "latitude": chosen["latitude"],
        "longitude": chosen["longitude"],
        "country": chosen.get("country"),
        "country_code": chosen.get("country_code"),
        "timezone": chosen.get("timezone"),
        "population": chosen.get("population"),
    }

# retourne la météo actuelle et les prévisions des prochains jours (default=3 jours)
def get_weather(latitude, longitude, days=3):
    data = get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
            "precipitation,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,wind_speed_10m_max",
            "forecast_days": days,
            "timezone": "auto",
        }
    )
    
    current = data.get("current")
    daily = data.get("daily")
    if not current and not daily:
        raise NoDataAvailable("Aucune donnée météo disponible pour ces coordonnées.")
    
    result = {
        "timezone": data.get("timezone"),
        "current": None,
        "forecast": []
    }
    
    if current:
        result["current"] = {
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_kmh": current.get("wind_speed_10m"),
            "condition": WEATHER_CODES.get(current.get("weather_code"), "Inconnu"),
        }
        
    if daily:
        for i, day in enumerate(daily.get("time", [])):
            result["forecast"].append({
                    "date": day,
                    "condition": WEATHER_CODES.get(daily["weather_code"][i], "Inconnu"),
                    "temp_min_c": daily["temperature_2m_min"][i],
                    "temp_max_c": daily["temperature_2m_max"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "wind_max_kmh": daily["wind_speed_10m_max"][i],
            })
            
    return result
