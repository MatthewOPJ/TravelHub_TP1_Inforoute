from django.shortcuts import render

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from integrations.aggregator import get_destination_details
from . import services
from .models import Activity, Destination, Participation, Trip
from .permissions import (
    CanEditTripContent,
    IsTripOwnerOrReadOnly,
    visible_trips,
)

from .serializers import (
    ActivitySerializer,
    AddParticipantSerializer,
    DestinationSerializer,
    DestinationWithActivitiesSerializer,
    ParticipationSerializer,
    TripDetailSerializer,
    TripSerializer,
)

User = get_user_model()

# trouve la date a partir de l'URL
def date_param(request, name):
    value = request.query_params.get(name)
    if not value:
        return None
    
    parsed = parse_date(value)
    if parsed is None:
        raise serializers.ValidationError({name: "Format de date invalide. Utilisez AAAA-MM-JJ."})
    
    return parsed

def number_param(request, name):
    value = request.query_params.get(name)
    if not value:
        return None
    
    try:
        return float(value)
    except ValueError:
        raise serializers.ValidationError({name: "Un nombre est attendu."})
    
class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTripOwnerOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = [
        "start_date", 
        "end_date", 
        "title", 
        "created_at"
    ]
    
    def get_serializer_class(self):
        return TripDetailSerializer if self.action == "retrieve" else TripSerializer
    
    def get_queryset(self):
        params = self.request.query_params
        trips = (
            visible_trips(self.request.user)
            .select_related("owner")
            .prefetch_related("destinations", "participations", "destinations__activities")
        )
        
        if params.get("status"):
            trips = trips.filter(status=params["status"])
            
        if params.get("q"):
            trips = trips.filter(
                Q(title__icontains=params["q"]) | Q(description__icontains=params["q"])
            )
            
        if params.get("owned") in ("1", "true", "True"):
            trips = trips.filter(owner=self.request.user)
            
        if date_param(self.request, "start_after"):
            trips = trips.filter(start_date__gte=date_param(self.request, "start_after"))
            
        if date_param(self.request, "start_before"):
            trips = trips.filter(start_date__lte=date_param(self.request, "start_before"))
            
        return trips
    
    @action(detail=True, methods=["get", "post"], url_path="participants")
    def participants(self, request, pk=None):
        trip = self.get_object()
        if request.method == "GET":
            serializer = ParticipationSerializer(
                trip.participations.select_related("user"),
                many=True
            )
            
            return Response(serializer.data)
        
        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, username=serializer.validated_data["username"])
        
        try:
            participation = services.add_participant(trip, user, serializer.validated_data["role"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        
        return Response(ParticipationSerializer(participation).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=["delete"], url_path=r"participants/(?P<user_id>\d+)")
    def remove_participant(self, request, pk=None, user_id=None):
        trip = self.get_object() # DELETE : propriétaire seulement
        if int(user_id) == trip.owner_id:
            raise serializers.ValidationError({"user_id": "Le propriétaire ne peut pas être retiré."})
        
        participation = get_object_or_404(Participation, trip=trip, user_id=user_id)
        participation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def duplicate(self, request, pk=None):
        trip = get_object_or_404(self.get_queryset(), pk=pk)
        copy = services.duplicate_trip(trip, request.user)
        return Response(
            TripSerializer(copy, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )
    
    
class DestinationViewSet(viewsets.ModelViewSet):
    serializer_class = DestinationSerializer
    permission_classes = [IsAuthenticated, CanEditTripContent]
    filter_backends = [OrderingFilter]
    ordering_fields = ["arrival_date", "departure_date", "city", "country"]
    
    def get_serializer_class(self):
        return DestinationWithActivitiesSerializer if self.action == "retrieve" else DestinationSerializer
    
    def get_queryset(self):
        params = self.request.query_params
        
        destinations = Destination.objects.filter(
            trip__in=visible_trips(self.request.user)
        ).select_related("trip").prefetch_related("activities")
        
        if params.get("trip"):
            destinations = destinations.filter(trip_id=params["trip"])
        if params.get("country"):
            destinations = destinations.filter(country__icontains=params["country"])
        if params.get("city"):
            destinations = destinations.filter(city__icontains=params["city"])
        return destinations
    
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        destination = self.get_object()
        return Response(get_destination_details(destination))
    
class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated, CanEditTripContent]
    filter_backends = [OrderingFilter]
    ordering_fields = ["date", "cost", "name"]
    
    def get_queryset(self):
        params = self.request.query_params
        
        activities = Activity.objects.filter(
            destination__trip__in=visible_trips(self.request.user)
        ).select_related("destination", "destination__trip")
        
        if params.get("destination"):
            activities = activities.filter(destination_id=params["destination"])
            
        if params.get("trip"):
            activities = activities.filter(destination__trip_id=params["trip"])
            
        if params.get("category"):
            activities = activities.filter(category=params["category"])
            
        if date_param(self.request, "date_from"):
            activities = activities.filter(date__gte=date_param(self.request, "date_from"))
            
        if date_param(self.request, "date_to"):
            activities = activities.filter(date__lte=date_param(self.request, "date_to"))
            
        if number_param(self.request, "min_cost") is not None:
            activities = activities.filter(cost__gte=number_param(self.request, "min_cost"))
            
        if number_param(self.request, "max_cost") is not None:
            activities = activities.filter(cost__lte=number_param(self.request, "max_cost"))
            
        return activities
