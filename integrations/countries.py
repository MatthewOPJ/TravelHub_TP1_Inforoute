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
