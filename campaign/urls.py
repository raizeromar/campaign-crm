from django.urls import path
from . import views

urlpatterns = [
    path('redirect/<str:ref_code>/', views.redirect_and_track, name='redirect_and_track'),

]
