from django.db.models import Count, Sum
from . import countries, open_meteo
from .exceptions import ExternalServiceError, LocationNotFound, NoDataAvailable

def make_block(source, status, data=None, message=None):
    return {
        "source": source, 
        "status": status, 
        "data": data, 
        "message": message
    }

# données de TravlHub, lues dans PostgreSQL
def internal_data(destination):
    activities = destination.activities.all()
    totals = activities.aggregate(total_cost=Sum("cost"), count=Count("id"))
    by_category = activities.values("category").annotate(count=Count("id"), cost=Sum("cost"))
    trip = destination.trip
    
    return {
        "id": destination.id,
        "city": destination.city,
        "country": destination.country,
        "arrival_date": destination.arrival_date,
        "departure_date": destination.departure_date,
        "trip": {
            "id": trip.id,
            "title": trip.title,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
        },
        "activities": [
        {
            "id": a.id,
            "name": a.name,
            "category": a.category,
            "date": a.date,
            "cost": a.cost,
        } for a in activities
        ],
        "activities_count": totals["count"],
        "activities_total_cost": totals["total_cost"] or 0,
        "activities_by_category": list(by_category),
    }
    
# combine les données DB, REST et GraphQL
def get_destination_details(destination):
    result = {
        "destination": internal_data(destination),
        "location": None,
        "weather": None,
        "country": None,
        "complete": False,
    }
    
    # Géocodage (Open-Meteo)
    location = None
    try:
        location = open_meteo.geocode(destination.city, destination.country)
        result["location"] = make_block("open-meteo", "ok", location)
    except LocationNotFound as exc:
        result["location"] = make_block("open-meteo", "not_found", message=str(exc))
    except ExternalServiceError as exc:
        result["location"] = make_block("open-meteo", "unavailable", message=str(exc))
        
    # Open-Meteo, REST
    if location:
        try:
            weather = open_meteo.get_weather(location["latitude"], location["longitude"])
            result["weather"] = make_block("open-meteo", "ok", weather)
        except NoDataAvailable as exc:
            result["weather"] = make_block("open-meteo", "no_data", message=str(exc))
        except ExternalServiceError as exc:
            result["weather"] = make_block("open-meteo", "unavailable", message=str(exc))
    else:
        result["weather"] = make_block(
            "open-meteo", 
            result["location"]["status"], 
            message="Destination non identifiée : météo indisponible."
        )
        
    # Pays, GraphQL
    if location:
        try:
            country = countries.get_country(location["country_code"])
            result["country"] = make_block("countries-graphql", "ok", country)
        except NoDataAvailable as exc:
            result["country"] = make_block("countries-graphql", "no_data", message=str(exc))
        except ExternalServiceError as exc:
            result["country"] = make_block("countries-graphql", "unavailable", message=str(exc))
    else:
        result["country"] = make_block(
            "countries-graphql", 
            result["location"]["status"], 
            message="Code pays inconnu : destination non identifiée."
        )
        
    result["complete"] = all(result[k]["status"] == "ok" for k in ("location", "weather", "country"))
    return result