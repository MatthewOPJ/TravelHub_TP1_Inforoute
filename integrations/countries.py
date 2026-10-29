import requests
from .exceptions import ExternalServiceError, NoDataAvailable
COUNTRIES_URL = "https://countries.trevorblades.com/graphql"
# en secondes
TIMEOUT = 8
# On demande juste les champs utiles à TravelHub
COUNTRY_QUERY = """
    query CountryInfo($code: ID!) {
        country(code: $code) {
            name
            native
            capital
            continent {
                name
            }
            currency
            languages {
                name
            }
        }
    }
"""



# prend le code ISO à 2 lettres et retourne les infos
# (nom, continent, capitale, etc)
def get_country_info(code):
    if not code:
        raise NoDataAvailable("Aucun code pays n'est disponible pour cette destination.")
    
    payload = {"query": COUNTRY_QUERY, "variables": {"code": code.upper()}}
    
    try:
        response = requests.post(COUNTRIES_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        body = response.json()
    except requests.Timeout as exc:
        raise ExternalServiceError("Countries GraphQL n'a pas répondu à temps.") from exc
    except requests.RequestException as exc:
        raise ExternalServiceError("Countries GraphQL est inaccessible ou a renvoyé une erreur.") from exc

    if body.get("errors"):
        raise ExternalServiceError("Countries GraphQL a renvoyé une erreur de requête.")
    
    country = (body.get("data") or {}).get("country")
    
    if not country:
        raise NoDataAvailable(f"Aucun pays trouvé pour le code « {code} ».")
    
    return {
        "name": country.get("name"),
        "native_name": country.get("native"),
        "capital": country.get("capital"),
        "continent": (country.get("continent") or {}).get("name"),
        "currencies": [c for c in (country.get("currency") or "").split(",") if c],
        "languages": [lang["name"] for lang in country.get("languages") or []],
    }
    