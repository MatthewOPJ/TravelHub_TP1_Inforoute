from rest_framework.routers import DefaultRouter
from .views import ActivityViewSet, DestinationViewSet, TripViewSet

router = DefaultRouter()

router.register("trips", TripViewSet, basename="trip")
router.register("destinations", DestinationViewSet, basename="destination")
router.register("activities", ActivityViewSet, basename="activity")

urlpatterns = router.urls
