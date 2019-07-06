from django.urls import path
from django.conf.urls import url

from . import views

urlpatterns = [
    path(r'service/', views.service, name='service'),
    path(r'log/', views.log, name='log'),
    path('', views.index, name='index'),
]