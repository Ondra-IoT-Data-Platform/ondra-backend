from django.contrib import admin
from customers.models import Customer, CustomerContact, DeliveryAddress

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "organization", "created_at"]
    search_fields = ("name",)
    list_filter = ["organization"]
    ordering = ("-created_at",)

@admin.register(CustomerContact)
class CustomerContactAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "full_name", "email", "phone_number", "is_active"]
    search_fields = ("customer__name", "full_name")
    list_filter = ["is_active"]
    ordering = ("-id",)

@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "label", "address", "is_default", "is_active"]
    search_fields = ("customer__name", "label", "address")
    list_filter = ["is_default", "is_active"]
    ordering = ("-id",)
