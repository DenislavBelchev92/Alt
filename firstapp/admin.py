from django.contrib import admin
from django.utils import timezone
from .models import (
    AltUser, Profile, SkillGroup, SkillSubgroup, SkillName, Skill, 
    CourseEnrollmentRequest, ApprovedCourseEnrollment, ScheduledCourse, CourseAttendance
)

# Register your models here.

@admin.register(AltUser)
class AltUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'sur_name', 'country', 'city']
    search_fields = ['user__username', 'name', 'sur_name', 'country', 'city']

@admin.register(CourseEnrollmentRequest)
class CourseEnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'course_full_name', 'status', 'requested_at', 'reviewed_by']
    list_filter = ['status', 'skill_group', 'requested_at', 'reviewed_at']
    search_fields = ['user__username', 'skill_group', 'skill_subgroup', 'skill_name']
    readonly_fields = ['requested_at', 'reviewed_at']
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        approved_count = 0
        for enrollment_request in queryset.filter(status='pending'):
            enrollment_request.status = 'approved'
            enrollment_request.reviewed_by = request.user
            enrollment_request.reviewed_at = timezone.now()
            enrollment_request.save()
            
            # Create approved enrollment
            ApprovedCourseEnrollment.objects.get_or_create(
                user=enrollment_request.user,
                skill_group=enrollment_request.skill_group,
                skill_subgroup=enrollment_request.skill_subgroup,
                skill_name=enrollment_request.skill_name,
                defaults={'enrollment_request': enrollment_request}
            )
            approved_count += 1
        
        self.message_user(request, f'Successfully approved {approved_count} enrollment requests.')
    approve_requests.short_description = "Approve selected enrollment requests"
    
    def reject_requests(self, request, queryset):
        rejected_count = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'Successfully rejected {rejected_count} enrollment requests.')
    reject_requests.short_description = "Reject selected enrollment requests"

@admin.register(ApprovedCourseEnrollment)
class ApprovedCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill_group', 'skill_subgroup', 'skill_name', 'enrolled_at']
    list_filter = ['skill_group', 'enrolled_at']
    search_fields = ['user__username', 'skill_group', 'skill_subgroup', 'skill_name']
    readonly_fields = ['enrolled_at']

@admin.register(ScheduledCourse)
class ScheduledCourseAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'instructor', 'scheduled_date', 'scheduled_time', 'max_students', 'enrolled_count']
    list_filter = ['skill_group', 'scheduled_date', 'instructor']
    search_fields = ['skill_group', 'skill_subgroup', 'skill_name', 'instructor__username']
    readonly_fields = ['created_at']
    
    def enrolled_count(self, obj):
        return obj.courseattendance_set.count()
    enrolled_count.short_description = 'Enrolled Students'

@admin.register(CourseAttendance)
class CourseAttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'scheduled_course', 'enrolled_at', 'attended']
    list_filter = ['attended', 'enrolled_at', 'scheduled_course__scheduled_date']
    search_fields = ['student__username', 'scheduled_course__skill_group']
    readonly_fields = ['enrolled_at']

admin.site.register(SkillGroup)
admin.site.register(SkillSubgroup)
admin.site.register(SkillName)
admin.site.register(Skill)
