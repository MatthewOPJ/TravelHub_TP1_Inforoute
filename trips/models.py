from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from . import validators

class Trip(models.Model): # Cette classe est pour le voyage, elle gère les informations liées au voyage ainsi que ses participants et ses propriétaires
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PLANNED = "planned", "Planifié"
        ONGOING = "ongoing", "En cours"
        COMPLETED = "completed", "Terminé"
        CANCELLED = "cancelled", "Annulé"
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_trips",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Participation",
        related_name="trips",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["start_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="trip_end_after_start",
            ),
        ]
        
    def __str__(self):
        return self.title
    
    def clean(self):
        validators.check_trip_dates(self.start_date, self.end_date)
        if self.pk:
            validators.check_trip_covers_destinations(self)

        
            
class Participation(models.Model): # Cette classe vient faire le lien entre son utilisateur(propriétaire) et le voyage en question
    class Role(models.TextChoices):
        OWNER = "owner", "Propriétaire"
        EDITOR = "editor", "Éditeur"
        VIEWER = "viewer", "Lecteur"
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="participations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participations",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    joined_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["trip", "user"], name="unique_participation"),
        ]
        
    def __str__(self):
        return f"{self.user} - {self.trip} ({self.role})"
    
    
    
class Destination(models.Model): # Cette classe gère les destinations différentes d'un voyage et leurs informations liées.
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="destinations")
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    arrival_date = models.DateField()
    departure_date = models.DateField()
    class Meta:
        ordering = ["arrival_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(departure_date__gte=F("arrival_date")),
                name="destination_departure_after_arrival",
            ),
        ]

    def __str__(self):
        return f"{self.city}, {self.country}"
    
    def clean(self):
        if not self.trip_id:
            return
        validators.check_destination_dates(self.trip, self.arrival_date, self.departure_date)
        if self.pk:
            validators.check_destination_covers_activities(self)
            
            

class Activity(models.Model): # Cette classe permet de gérer les actions(planifier, catégoriser, etc) de chaque activité par destination.
    class Category(models.TextChoices):
        CULTURE = "culture", "Culture"
        FOOD = "food", "Gastronomie"
        SPORT = "sport", "Sport"
        NATURE = "nature", "Nature"
        TRANSPORT = "transport", "Transport"
        LEISURE = "leisure", "Loisirs"
        OTHER = "other", "Autre"
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE,
        related_name="activities")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    date = models.DateField()
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    class Meta:
        ordering = ["date", "id"]
        verbose_name_plural = "activities"
        constraints = [
            models.CheckConstraint(condition=Q(cost__gte=0), name="activity_cost_positive"),
        ]
    def __str__(self):
        return self.name
    
    def clean(self):
        if not self.destination_id:
            return
        validators.check_activity_date(self.destination, self.date)