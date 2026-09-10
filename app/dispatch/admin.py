from django.contrib import admin
from dispatch.models import Dispatch, TripMetadata


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    pass


@admin.register(TripMetadata)
class TripMetadataAdmin(admin.ModelAdmin):
    pass
