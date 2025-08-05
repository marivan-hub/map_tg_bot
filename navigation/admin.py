from django.contrib import admin
from .models import Building, Route, Step

class StepInline(admin.TabularInline):
    model = Step
    extra = 1

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('room_code', 'building', 'floor')
    inlines = [StepInline]

admin.site.register(Building)
