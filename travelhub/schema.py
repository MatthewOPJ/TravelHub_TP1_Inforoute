import json
import graphene
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.serializers.json import DjangoJSONEncoder
from graphene.types.generic import GenericScalar
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from integrations.aggregator import get_destination_details
from trips import services
from trips.models import Activity, Destination, Participation, Trip
from trips.permissions import can_edit_content, is_owner, visible_trips

User = get_user_model()

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username")  # jamais le mot de passe ni le courriel
        
class ParticipationType(DjangoObjectType):
    class Meta:
        model = Participation
        fields = ("id", "user", "role", "joined_at")
        
class ActivityType(DjangoObjectType):
    class Meta:
        model = Activity
        fields = ("id", "name", "description", "category", "date", "cost", "destination")
        
class DestinationType(DjangoObjectType):
    class Meta:
        model = Destination
        fields = ("id", "city", "country", "arrival_date", "departure_date", "trip", "activities")
        
class TripType(DjangoObjectType):
    class Meta:
        model = Trip
        fields = (
            "id", "title", "description", "start_date", "end_date", "status",
            "owner", "participations", "destinations", "created_at",
        )
        
def require_user(info):
    user = info.context.user
    if not user.is_authenticated:
        raise GraphQLError("Authentification requise.")
    return user

def get_or_error(queryset, pk, label):
    try:
        return queryset.get(pk=pk)
    except (queryset.model.DoesNotExist, ValueError, TypeError):
        raise GraphQLError(f"{label} introuvable.")
    
def get_trip(user, trip_id):
    return get_or_error(visible_trips(user), trip_id, "Voyage")

def get_destination(user, destination_id):
    queryset = Destination.objects.filter(trip__in=visible_trips(user)).select_related("trip")
    return get_or_error(queryset, destination_id, "Destination")

def get_activity(user, activity_id):
    queryset = Activity.objects.filter(destination__trip__in=visible_trips(user)).select_related(
        "destination", "destination__trip"
    )
    return get_or_error(queryset, activity_id, "Activité")
def check_can_edit(user, trip):
    if not can_edit_content(user, trip):
        raise GraphQLError("Vous n'avez pas le droit de modifier ce voyage.")
    
def save_or_error(instance):
    """Valide avec les règles du modèle (full_clean) puis enregistre."""
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise GraphQLError(" ".join(exc.messages))
    instance.save()
    return instance
ORDER_FIELDS = {
    "start_date", "-start_date", "end_date", "-end_date",
    "title", "-title", "created_at", "-created_at",
}