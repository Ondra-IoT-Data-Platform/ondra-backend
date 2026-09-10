from config.exceptions import register_exception_handlers
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from ninja import NinjaAPI

from access.views import router as access_router
from terminals.views import router as terminal_router
from organization.views import router as organization_router
from users.views import router as user_router
from customers.views import router as customer_router
from dispatch.views import router as dispatch_router
from fleet.views import router as fleet_router
# from eta.views import router as eta_router
from rfid_events.views import router as rfid_router

app_v1 = NinjaAPI(
    title="Ondra IoT Data Platform API",
    description="API for the Ondra IoT Data Platform",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi",
)

app_v1.add_router("access", access_router)
app_v1.add_router("users", user_router)
app_v1.add_router("terminals", terminal_router)
app_v1.add_router("organizations", organization_router)
app_v1.add_router("fleet", fleet_router)
app_v1.add_router("dispatch", dispatch_router)
app_v1.add_router("customers", customer_router)
app_v1.add_router("rfid", rfid_router)
# app_v1.add_router("eta", eta_router)



register_exception_handlers(app_v1)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", app_v1.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
