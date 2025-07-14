from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
    path('update_skill/<str:skill_name>/', views.update_skill, name='update_skill'),
    path('add_skill', views.add_skill, name='add_skill'),

]
