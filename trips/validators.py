from django.core.exceptions import ValidationError
from django.db.models import Max, Min

def check_trip_dates(start_date, end_date): #La date de fin ne peut pas précéder la date de début.
    if start_date and end_date and end_date < start_date:
        raise ValidationError(
            {"end_date": "La date de fin doit être égale ou postérieure à la date de début."}
        )
        
def check_trip_covers_destinations(trip):  #Si on change les dates d'un voyage, les destinations existantes doivent rester dedans.
    if not (trip.start_date and trip.end_date):
        return
    limits = trip.destinations.aggregate(first=Min("arrival_date"), last=Max("departure_date"))
    if limits["first"] and limits["first"] < trip.start_date:
        raise ValidationError(
            {"start_date": "Une destination arrive avant cette date de début."}
        )
    if limits["last"] and limits["last"] > trip.end_date:
        raise ValidationError(
            {"end_date": "Une destination part après cette date de fin."}
        )