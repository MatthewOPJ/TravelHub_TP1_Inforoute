from django.core.exceptions import ValidationError
from django.db.models import Max, Min

def check_trip_dates(start_date, end_date): # La date de fin ne peut pas précéder la date de début.
    if start_date and end_date and end_date < start_date:
        raise ValidationError(
            {"end_date": "La date de fin doit être égale ou postérieure à la date de début."}
        )
        
def check_trip_covers_destinations(trip):  # Si on change les dates d'un voyage, les destinations existantes doivent rester dedans.
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
        
def check_destination_dates(trip, arrival_date, departure_date): # Les dates d'une destination doivent être cohérentes et rester dans celles du voyage.
    if arrival_date and departure_date and departure_date < arrival_date:
        raise ValidationError(
            {"departure_date": "La date de départ doit être égale ou postérieure à la date d'arrivée."}
        )
    if arrival_date and arrival_date < trip.start_date:
        raise ValidationError(
            {"arrival_date": "L'arrivée ne peut pas précéder le début du voyage."}
        )
    if departure_date and departure_date > trip.end_date:
        raise ValidationError(
            {"departure_date": "Le départ ne peut pas dépasser la fin du voyage."}
        )
        
def check_destination_covers_activities(destination): # Si on change les dates d'une destination, ses activités doivent rester dedans.
    if not (destination.arrival_date and destination.departure_date):
        return
    limits = destination.activities.aggregate(first=Min("date"), last=Max("date"))
    if limits["first"] and limits["first"] < destination.arrival_date:
        raise ValidationError(
            {"arrival_date": "Une activité a lieu avant cette date d'arrivée."}
        )
    if limits["last"] and limits["last"] > destination.departure_date:
        raise ValidationError(
            {"departure_date": "Une activité a lieu après cette date de départ."}
        )
        
def check_activity_date(destination, date): # La date d'une activité doit tomber pendant le séjour dans la destination.
    if date and not (destination.arrival_date <= date <= destination.departure_date):
        raise ValidationError(
            {"date": "La date de l'activité doit être comprise entre l'arrivée et le départ de la destination."}
        )