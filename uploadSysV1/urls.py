from django.urls import path
from .views import *

urlpatterns = [
    path('',loginView,name='login'),
    path('register/',registerView,name='register'),
    path('upload/',uploadView, name='upload'),
    path('admin-login/', adminLoginView, name='admin_login'),
    path('admindash/', adminDashboardView, name='admin_dashboard'),
    path('admin-logout', adminLogoutView, name='admin_logout'),
    path('logout', LogoutView, name='logout'),
    path('delete-project/<int:pk>/', delete_project, name='delete_project'),
    path('grade-project/<int:pk>/', grade_project, name='grade_project'),
]