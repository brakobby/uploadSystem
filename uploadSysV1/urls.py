from django.urls import path
from .views import *

urlpatterns = [
    path('',loginView,name='login'),
    path('register/',registerView,name='register'),
    path('upload/',uploadView, name='upload'),
    path('admin-login/', adminLoginView, name='admin_login'),
    path('admindash/', adminDashboardView, name='admin_dashboard'),
    path('admin-logout', adminLogoutView, name='admin_logout')
]