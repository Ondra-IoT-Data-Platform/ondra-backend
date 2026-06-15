from config.exceptions import register_exception_handlers
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from app.access.views import router as access_router

app_v1 = NinjaAPI(
    title="Ondra IoT Data Platform API",
    description="API for the Ondra IoT Data Platform",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi",
)

app_v1.add_router("access/", access_router)


register_exception_handlers(app_v1)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", app_v1.urls),
]
