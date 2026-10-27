from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Activity, Destination, Participation, Trip

@transaction.atomic
def create_trip(*, owner, **data): # Cette fonction va créer le voyage et la participation du propriétaire du voyage : les deux ou aucun (transaction).
    trip = Trip(owner=owner, **data)
    trip.full_clean()
    trip.save()
    Participation.objects.create(trip=trip, user=owner, role=Participation.Role.OWNER)
    return trip

@transaction.atomic
def duplicate_trip(trip, user): # Cette fonction va copier les voyages avec leurs informations. Si 1 erreur est détecté durant ces événements, tous est annulé.
    copy = create_trip(
        owner=user,
        title=f"Copie de {trip.title}"[:150],
        description=trip.description,
        start_date=trip.start_date,
        end_date=trip.end_date,
        status=Trip.Status.DRAFT,
    )
    for destination in trip.destinations.all():
        new_destination = Destination.objects.create(
            trip=copy,
            city=destination.city,
            country=destination.country,
            arrival_date=destination.arrival_date,
            departure_date=destination.departure_date,
        )
        Activity.objects.bulk_create(
            [
                Activity(
                    destination=new_destination,
                    name=activity.name,
                    description=activity.description,
                    category=activity.category,
                    date=activity.date,
                    cost=activity.cost,
                )
                for activity in destination.activities.all()
            ]
        )
    return copy

def add_participant(trip, user, role): # Cette fonction est là afin de vérifier qu'on ne mets pas 2 fois le même participant.
    if role == Participation.Role.OWNER:
        raise ValidationError({"role": "Un voyage n'a qu'un seul propriétaire."})
    if trip.owner_id == user.id or Participation.objects.filter(trip=trip, user=user).exists():
        raise ValidationError({"username": "Cet utilisateur participe déjà au voyage."})
    return Participation.objects.create(trip=trip, user=user, role=role)