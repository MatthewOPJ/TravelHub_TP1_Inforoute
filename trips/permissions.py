from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission
from .models import Participation, Trip

# retourne le lien de l'utilisateur avec le voyage (owner, editor, viewer)
def get_role(user, trip):
    if not user.is_authenticated:
        return None
    
    if trip.owner_id == user.id:
        return Participation.Role.OWNER
    
    participation = Participation.objects.filter(trip=trip, user=user).first()
    
    if participation:
        return participation.role
    return None

# fonctions de help

def can_view(user, trip):
    return user.is_authenticated and (user.is_staff or get_role(user, trip))

def is_owner(user, trip):
    return user.is_authenticated and (user.is_staff or trip.owner_id == user.id)

# basically "if owner ou admin"
def can_edit_content(user, trip):
    if not user.is_authenticated:
        return False
    
    return user.is_staff or get_role(user, trip) in (
        Participation.Role.OWNER,
        Participation.Role.EDITOR,
    )
    
# retourne la liste des voyages auquel l'utilisateur participe ou organise
def visible_trips(user):
    if not user.is_authenticated:
        return Trip.objects.none()
    if user.is_staff:
        return Trip.objects.all()
    return Trip.objects.filter(Q(owner=user) | Q(participations__user=user)).distinct()


class IsTripOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return can_view(request.user, obj)
        return is_owner(request.user, obj)
    
    
class CanEditTripContent(BasePermission):
    def has_object_permission(self, request, view, obj):
        trip = obj.trip if hasattr(obj, "trip") else obj.destination.trip
        
        if request.method in SAFE_METHODS:
            return can_view(request.user, trip)
        return can_edit_content(request.user, trip)
    