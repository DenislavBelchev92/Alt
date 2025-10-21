from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile_edit/', views.profile_edit, name='profile_edit'),
    path('logout/', views.logout, name='logout'),
    path('update_skill/<int:skill_id>/', views.update_skill, name='update_skill'),
    path('delete_skill/<int:skill_id>/', views.delete_skill, name='delete_skill'),
    path('add_skill', views.add_skill, name='add_skill'),
    path('lessons/<path:group_name>/<path:subgroup_name>/<path:skill_name>/', views.lessons, name='lessons'),
    path('private-lesson/', views.private_lesson, name='private_lesson'),

]
