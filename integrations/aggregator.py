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
