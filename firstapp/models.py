from django.contrib.auth.models import AbstractUser
from django.db import models

# Constants
MAX_PARTICIPANTS_PER_COURSE = 16

def user_profile_picture_path(instance, filename):
    """Generate upload path for user profile pictures"""
    return f'profile_pics/{instance.user.username}_{filename}'

class AltUser(AbstractUser):

    def get_skills(self):
        grouped = {}
        for skill in self.skill.all():
            group = skill.name.subgroup.group.name
            subgroup = skill.name.subgroup.name
            if group not in grouped:
                grouped[group] = {}
            if subgroup not in grouped[group]:
                grouped[group][subgroup] = []
            grouped[group][subgroup].append(skill)
        return grouped
    
class Profile(models.Model):
    user = models.OneToOneField(AltUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    sur_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    age = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, blank=True, null=True)

    def __str__(self):
        return self.user.username
    
class SkillGroup(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class SkillSubgroup(models.Model):
    group = models.ForeignKey(SkillGroup, on_delete=models.CASCADE, related_name='skill_subgroups')
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"

class SkillName(models.Model):
    subgroup = models.ForeignKey(SkillSubgroup, on_delete=models.CASCADE, related_name='skill_names')
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"

class Skill(models.Model):
    name = models.ForeignKey(SkillName, on_delete=models.CASCADE)
    group = models.CharField(max_length=50, default="Unknown")
    subgroup = models.CharField(max_length=50, default="Unknown")
    user = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='skill')
    level = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure level is always between 0 and 100
        self.level = min(max(self.level, 0), 100)
        super().save(*args, **kwargs)

class CourseEnrollmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='enrollment_requests')
    skill_group = models.CharField(max_length=200)  # e.g., "Math"
    skill_subgroup = models.CharField(max_length=200)  # e.g., "Practical Math"
    skill_name = models.CharField(max_length=200)  # e.g., "Money and Shopping"
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(AltUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    admin_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'skill_group', 'skill_subgroup', 'skill_name']
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.skill_group}/{self.skill_subgroup}/{self.skill_name} ({self.status})"
    
    @property
    def course_full_name(self):
        return f"{self.skill_group} > {self.skill_subgroup} > {self.skill_name}"

class ApprovedCourseEnrollment(models.Model):
    """Track users who have been approved and enrolled in courses"""
    user = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='approved_enrollments')
    skill_group = models.CharField(max_length=200)
    skill_subgroup = models.CharField(max_length=200)
    skill_name = models.CharField(max_length=200)
    enrollment_request = models.OneToOneField(CourseEnrollmentRequest, on_delete=models.CASCADE, related_name='approved_enrollment')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'skill_group', 'skill_subgroup', 'skill_name']
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.user.username} enrolled in {self.skill_group}/{self.skill_subgroup}/{self.skill_name}"
    
    @classmethod
    def get_course_count(cls, skill_group, skill_subgroup, skill_name):
        """Get the number of approved enrollments for a specific course"""
        return cls.objects.filter(
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name
        ).count()
    
    @classmethod
    def get_course_participants(cls, skill_group, skill_subgroup, skill_name):
        """Get all approved participants for a specific course with their enrollment details"""
        return cls.objects.filter(
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name
        ).select_related('user', 'enrollment_request').order_by('enrolled_at')
    
    @classmethod
    def can_add_participant(cls, skill_group, skill_subgroup, skill_name):
        """Check if more participants can be added to a course"""
        current_count = cls.get_course_count(skill_group, skill_subgroup, skill_name)
        return current_count < MAX_PARTICIPANTS_PER_COURSE
    
    @classmethod
    def get_available_spots(cls, skill_group, skill_subgroup, skill_name):
        """Get the number of available spots for a course"""
        current_count = cls.get_course_count(skill_group, skill_subgroup, skill_name)
        return MAX_PARTICIPANTS_PER_COURSE - current_count

class ScheduledCourse(models.Model):
    """Track scheduled courses with specific dates and times"""
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'), 
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    skill_group = models.CharField(max_length=200)
    skill_subgroup = models.CharField(max_length=200)
    skill_name = models.CharField(max_length=200)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    instructor = models.ForeignKey(AltUser, on_delete=models.CASCADE, related_name='scheduled_courses')
    max_students = models.PositiveIntegerField(default=20)
    enrolled_students = models.ManyToManyField(AltUser, through='CourseAttendance', related_name='enrolled_courses')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        unique_together = ['skill_group', 'skill_subgroup', 'skill_name', 'scheduled_date', 'scheduled_time']
    
    def __str__(self):
        return f"{self.skill_group}/{self.skill_subgroup}/{self.skill_name} - {self.scheduled_date} {self.scheduled_time}"
    
    @property
    def course_full_name(self):
        return f"{self.skill_group} > {self.skill_subgroup} > {self.skill_name}"
    
    @property
    def available_spots(self):
        return self.max_students - self.enrolled_students.count()
    
    @property
    def is_full(self):
        return self.available_spots <= 0

class CourseAttendance(models.Model):
    """Track which students are enrolled in which scheduled courses"""
    student = models.ForeignKey(AltUser, on_delete=models.CASCADE)
    scheduled_course = models.ForeignKey(ScheduledCourse, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['student', 'scheduled_course']
    
    def __str__(self):
        return f"{self.student.username} in {self.scheduled_course}"