from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from . import validators

class Trip(models.Model):
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
    
    def clean(self): # Cette fonction est là pour aller vérifier les dates des voyages
        validators.check_trip_dates(self.start_date, self.end_date)
        if self.pk:
            validators.check_trip_covers_destinations(self)
            
class Participation(models.Model): # Cette class vient faire le lien entre son utilisateur(propriétaire) et le voyage en question
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