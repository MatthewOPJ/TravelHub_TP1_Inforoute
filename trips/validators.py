from django.core.exceptions import ValidationError
from django.db.models import Max, Min

def check_trip_dates(start_date, end_date): #La date de fin ne peut pas précéder la date de début.
    if start_date and end_date and end_date < start_date:
        raise ValidationError(
            {"end_date": "La date de fin doit être égale ou postérieure à la date de début."}
        )