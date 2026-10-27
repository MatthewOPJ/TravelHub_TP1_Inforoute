from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Activity, Destination, Participation, Trip

@transaction.atomic
def create_trip(*, owner, **data): #"Cette fonction va créer le voyage et la participation du propriétaire du voyage : les deux ou aucun (transaction).
    trip = Trip(owner=owner, **data)
    trip.full_clean()
    trip.save()
    Participation.objects.create(trip=trip, user=owner, role=Participation.Role.OWNER)
    return trip