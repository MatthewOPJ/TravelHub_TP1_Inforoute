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

