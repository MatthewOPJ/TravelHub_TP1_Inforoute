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


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)
    trips = graphene.List(
        TripType,
        status=graphene.String(),
        search=graphene.String(),
        order_by=graphene.String(),
    )
    trip = graphene.Field(TripType, id=graphene.ID(required=True))
    destinations = graphene.List(DestinationType, trip_id=graphene.ID(), country=graphene.String())
    activities = graphene.List(
        ActivityType,
        destination_id=graphene.ID(),
        category=graphene.String(),
        min_cost=graphene.Float(),
        max_cost=graphene.Float(),
        date_from=graphene.Date(),
        date_to=graphene.Date(),
    )
    destination_details = graphene.Field(GenericScalar, id=graphene.ID(required=True))
    
    def resolve_me(root, info):
        return require_user(info)
    
    def resolve_trips(root, info, status=None, search=None, order_by=None):
        trips = visible_trips(require_user(info))
        if status:
            trips = trips.filter(status=status)
        if search:
            trips = trips.filter(title__icontains=search)
        if order_by:
            if order_by not in ORDER_FIELDS:
                raise GraphQLError(f"Tri non permis. Valeurs possibles : {sorted(ORDER_FIELDS)}")
            trips = trips.order_by(order_by)
        return trips
    
    def resolve_trip(root, info, id):
        return get_trip(require_user(info), id)
    
    def resolve_destinations(root, info, trip_id=None, country=None):
        user = require_user(info)
        destinations = Destination.objects.filter(trip__in=visible_trips(user))
        if trip_id:
            destinations = destinations.filter(trip_id=trip_id)
        if country:
            destinations = destinations.filter(country__icontains=country)
        return destinations
    
    def resolve_activities(
        root, info, destination_id=None, category=None, min_cost=None, max_cost=None,
        date_from=None, date_to=None,
    ):
        user = require_user(info)
        activities = Activity.objects.filter(destination__trip__in=visible_trips(user))
        if destination_id:
            activities = activities.filter(destination_id=destination_id)
        if category:
            activities = activities.filter(category=category)
        if min_cost is not None:
            activities = activities.filter(cost__gte=min_cost)
        if max_cost is not None:
            activities = activities.filter(cost__lte=max_cost)
        if date_from:
            activities = activities.filter(date__gte=date_from)
        if date_to:
            activities = activities.filter(date__lte=date_to)
        return activities
    
    def resolve_destination_details(root, info, id):
        destination = get_destination(require_user(info), id)
        details = get_destination_details(destination)
        return json.loads(json.dumps(details, cls=DjangoJSONEncoder))  # dates et Decimal -> texte
    
# Mutations pour Trips avec les options Create, Update et Delete
class CreateTrip(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String()
        start_date = graphene.Date(required=True)
        end_date = graphene.Date(required=True)
        status = graphene.String()
    trip = graphene.Field(TripType)
    @classmethod
    def mutate(cls, root, info, **data):
        user = require_user(info)
        try:
            trip = services.create_trip(owner=user, **data)  # transaction : voyage + participation
        except DjangoValidationError as exc:
            raise GraphQLError(" ".join(exc.messages))
        return CreateTrip(trip=trip)
    
class UpdateTrip(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()
        description = graphene.String()
        start_date = graphene.Date()
        end_date = graphene.Date()
        status = graphene.String()
    trip = graphene.Field(TripType)
    @classmethod
    def mutate(cls, root, info, id, **data):
        user = require_user(info)
        trip = get_trip(user, id)
        if not is_owner(user, trip):
            raise GraphQLError("Seul le propriétaire peut modifier ce voyage.")
        for field, value in data.items():
            setattr(trip, field, value)
        return UpdateTrip(trip=save_or_error(trip))
    
class DeleteTrip(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    @classmethod
    def mutate(cls, root, info, id):
        user = require_user(info)
        trip = get_trip(user, id)
        if not is_owner(user, trip):
            raise GraphQLError("Seul le propriétaire peut supprimer ce voyage.")
        trip.delete()
        return DeleteTrip(ok=True)
    
# Mutations pour Destinations avec les options Create, Update et Delete
class CreateDestination(graphene.Mutation):
    class Arguments:
        trip_id = graphene.ID(required=True)
        city = graphene.String(required=True)
        country = graphene.String(required=True)
        arrival_date = graphene.Date(required=True)
        departure_date = graphene.Date(required=True)
    destination = graphene.Field(DestinationType)
    @classmethod
    def mutate(cls, root, info, trip_id, **data):
        user = require_user(info)
        trip = get_trip(user, trip_id)
        check_can_edit(user, trip)
        return CreateDestination(destination=save_or_error(Destination(trip=trip, **data)))
    
class UpdateDestination(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        city = graphene.String()
        country = graphene.String()
        arrival_date = graphene.Date()
        departure_date = graphene.Date()
    destination = graphene.Field(DestinationType)
    @classmethod
    def mutate(cls, root, info, id, **data):
        user = require_user(info)
        destination = get_destination(user, id)
        check_can_edit(user, destination.trip)
        for field, value in data.items():
            setattr(destination, field, value)
        return UpdateDestination(destination=save_or_error(destination))
    
class DeleteDestination(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    @classmethod
    def mutate(cls, root, info, id):
        user = require_user(info)
        destination = get_destination(user, id)
        check_can_edit(user, destination.trip)
        destination.delete()
        return DeleteDestination(ok=True)
    
# Mutations pour Activities avec les options Create, Update et Delete
class CreateActivity(graphene.Mutation):
    class Arguments:
        destination_id = graphene.ID(required=True)
        name = graphene.String(required=True)
        description = graphene.String()
        category = graphene.String()
        date = graphene.Date(required=True)
        cost = graphene.Float()
    activity = graphene.Field(ActivityType)
    @classmethod
    def mutate(cls, root, info, destination_id, **data):
        user = require_user(info)
        destination = get_destination(user, destination_id)
        check_can_edit(user, destination.trip)
        return CreateActivity(activity=save_or_error(Activity(destination=destination, **data)))
    
class UpdateActivity(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        description = graphene.String()
        category = graphene.String()
        date = graphene.Date()
        cost = graphene.Float()
    activity = graphene.Field(ActivityType)
    @classmethod
    def mutate(cls, root, info, id, **data):
        user = require_user(info)
        activity = get_activity(user, id)
        check_can_edit(user, activity.destination.trip)
        for field, value in data.items():
            setattr(activity, field, value)
        return UpdateActivity(activity=save_or_error(activity))
    
class DeleteActivity(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Boolean()
    @classmethod
    def mutate(cls, root, info, id):
        user = require_user(info)
        activity = get_activity(user, id)
        check_can_edit(user, activity.destination.trip)
        activity.delete()
        return DeleteActivity(ok=True)