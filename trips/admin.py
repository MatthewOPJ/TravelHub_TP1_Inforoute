from django.contrib import admin

from .models import Activity, Destination, Participation, Trip
class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 0
    
class DestinationInline(admin.TabularInline):
    model = Destination
    extra = 0
    
class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    
@admin.register(Trip)

class TripAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "start_date", "end_date")
    list_filter = ("status", "start_date")
    search_fields = ("title", "description", "owner__username")
    date_hierarchy = "start_date"
    inlines = [ParticipationInline, DestinationInline]
    
@admin.register(Destination)

class DestinationAdmin(admin.ModelAdmin):
    list_display = ("city", "country", "trip", "arrival_date", "departure_date")
    list_filter = ("country",)
    search_fields = ("city", "country", "trip__title")
    inlines = [ActivityInline]
    
@admin.register(Activity)

class ActivityAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "destination", "date", "cost")
    list_filter = ("category", "date")
    search_fields = ("name", "description", "destination__city")
    
@admin.register(Participation)

class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("user", "trip", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("user__username", "trip__title")