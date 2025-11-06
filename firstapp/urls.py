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
    
    # Course management URLs
    path('course-management/', views.course_management, name='course_management'),
    path('course-management/process-enrollment/<int:request_id>/', views.process_enrollment_request, name='process_enrollment_request'),
    path('api/request-course-enrollment/', views.request_course_enrollment, name='request_course_enrollment'),
    path('api/check-course-enrollment/', views.check_course_enrollment_status, name='check_course_enrollment_status'),
    path('api/schedule-course/', views.schedule_course, name='schedule_course'),
    path('api/get-existing-sessions/', views.get_existing_sessions, name='get_existing_sessions'),
    path('api/add-to-existing-session/', views.add_to_existing_session, name='add_to_existing_session'),
    path('debug/enrollment/', views.debug_enrollment, name='debug_enrollment'),
    path('course-admin/<path:skill_group>/<path:skill_subgroup>/<path:skill_name>/', views.course_detail, name='course_detail'),

]
