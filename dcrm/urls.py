from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cloned/', include('website.urls')),
    path('campaign/', include('campaign.urls')),
]
