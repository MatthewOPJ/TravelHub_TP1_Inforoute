import copy
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import Activity, Destination, Participation, Trip
from .permissions import can_edit_content, can_view

User = get_user_model()

def run_model_clean(instance):
    try:
        instance.clean()
    except DjangoValidationError as exc:
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        raise serializers.ValidationError(detail)
    

def merged_instance(serializer, attrs, model):
    instance = copy.copy(serializer.instance) if serializer.instance else model()
    
    for key, value in attrs.items():
        setattr(instance, key, value)
        
    return instance


# serializers pour la BD


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]
        
        
        
class ParticipationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Participation
        fields = ["id", "user", "role", "joined_at"]
 
 
 
class AddParticipantSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=[Participation.Role.EDITOR, Participation.Role.VIEWER],
        default=Participation.Role.VIEWER,
    )
    
    
class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "destination", "name", "description", "category", "date", "cost"]
        def validate_destination(self, destination):
            user = self.context["request"].user
            
            if self.instance and destination != self.instance.destination:
                raise serializers.ValidationError("Une activité ne peut pas changer de destination.")
            if not can_view(user, destination.trip):
                raise serializers.ValidationError("Cette destination n'existe pas.")
            if not can_edit_content(user, destination.trip):
                raise PermissionDenied("Vous n'avez pas le droit de modifier ce voyage.")
            
            return destination
        
        def validate(self, attrs):
            run_model_clean(merged_instance(self, attrs, Activity))
            return attrs
        
        
        
class DestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destination
        fields = ["id", "trip", "city", "country", "arrival_date", "departure_date"]
        def validate_trip(self, trip):
            user = self.context["request"].user
            
            if self.instance and trip != self.instance.trip:
                raise serializers.ValidationError("Une destination ne peut pas changer de voyage.")
            if not can_view(user, trip):
                raise serializers.ValidationError("Ce voyage n'existe pas.")
            if not can_edit_content(user, trip):
                raise PermissionDenied("Vous n'avez pas le droit de modifier ce voyage.")
            
            return trip
        
        def validate(self, attrs):
            run_model_clean(merged_instance(self, attrs, Destination))
            return attrs
        
        
# quel nom de merde lol, mais ca a la mérite d'etre clair
class DestinationWithActivitiesSerializer(DestinationSerializer):
    activities = ActivitySerializer(many=True, read_only=True)
    class Meta(DestinationSerializer.Meta):
        fields = DestinationSerializer.Meta.fields + ["activities"]
        
        
        
# blah blah, trips serializer, cest facile ca
class TripSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()
    destinations_count = serializers.SerializerMethodField()
    class Meta:
        model = Trip
        fields = [
            "id", "title", "description", "start_date", "end_date", "status",
            "owner", "my_role", "destinations_count", "created_at", "updated_at",
        ]
        
        def get_my_role(self, trip) -> str | None:
            user = self.context["request"].user
            if trip.owner_id == user.id:
                return Participation.Role.OWNER
            for participation in trip.participations.all():
                if participation.user_id == user.id:
                    return participation.role
            return None
        
        def get_destinations_count(self, trip) -> int:
            return len(trip.destinations.all())
        
        def validate(self, attrs):
            run_model_clean(merged_instance(self, attrs, Trip))
            return attrs
        
        def create(self, validated_data):
            from . import services # import local, pour éviter que ca chiale
            return services.create_trip(owner=self.context["request"].user, **validated_data)
        


class TripDetailSerializer(TripSerializer):
    destinations = DestinationWithActivitiesSerializer(many=True, read_only=True)
    participations = ParticipationSerializer(many=True, read_only=True)
    class Meta(TripSerializer.Meta):
        fields = TripSerializer.Meta.fields + ["destinations", "participations"]