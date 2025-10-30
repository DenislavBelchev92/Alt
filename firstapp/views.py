from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Skill, SkillName, CourseEnrollmentRequest, ApprovedCourseEnrollment, ScheduledCourse, CourseAttendance
from .forms import SkillForm, ProfileForm
import yaml
import os
import json
from django.conf import settings

User = get_user_model()

def load_skills_yaml():
    """Load skills data from YAML file"""
    yaml_path = os.path.join(settings.BASE_DIR, 'firstapp', 'skills.yaml')
    try:
        with open(yaml_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return []

def index(request):
    """Display main page with upcoming scheduled courses"""
    from datetime import date, timedelta
    
    # Get the selected week from the request, default to current week
    selected_date = request.GET.get('week')
    if selected_date:
        try:
            current_date = date.fromisoformat(selected_date)
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()
    
    # Calculate the start of the week (Monday)
    days_since_monday = current_date.weekday()
    week_start = current_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    # Get scheduled courses for the selected week
    upcoming_courses = ScheduledCourse.objects.filter(
        scheduled_date__gte=week_start,
        scheduled_date__lte=week_end,
        is_active=True
    ).order_by('scheduled_date', 'scheduled_time')
    
    # Group courses by date for better display
    courses_by_date = {}
    for course in upcoming_courses:
        date_str = course.scheduled_date.strftime('%Y-%m-%d')
        if date_str not in courses_by_date:
            courses_by_date[date_str] = []
        courses_by_date[date_str].append(course)
    
    # Calculate navigation dates
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    
    return render(request, 'index.html', {
        'upcoming_courses': upcoming_courses,
        'courses_by_date': courses_by_date,
        'week_start': week_start,
        'week_end': week_end,
        'current_date': current_date,
        'prev_week': prev_week,
        'next_week': next_week,
        'selected_week': week_start.strftime('%Y-%m-%d'),
    })

def lessons(request, group_name, subgroup_name, skill_name):
    """Display lessons for a specific skill"""
    from .forms import get_skill_lessons
    from urllib.parse import unquote
    
    # URL decode the parameters
    group_name = unquote(group_name)
    subgroup_name = unquote(subgroup_name)
    skill_name = unquote(skill_name)
    
    # Get lessons from YAML
    lessons_list = get_skill_lessons(group_name, subgroup_name, skill_name)
    
    context = {
        'group_name': group_name,
        'subgroup_name': subgroup_name,
        'skill_name': skill_name,
        'lessons': lessons_list,
    }
    
    return render(request, 'lessons.html', context)

def private_lesson(request):
    """Handle private lesson booking requests"""
    from .forms import PrivateLessonForm
    from datetime import datetime, date, timedelta, time
    import json
    
    # Generate available time slots for the next 4 weeks (weekdays 7-8PM and 8-9PM)
    available_slots = []
    today = date.today()
    
    for week in range(4):  # Next 4 weeks
        week_start = today + timedelta(weeks=week)
        # Find Monday of this week
        days_since_monday = week_start.weekday()
        monday = week_start - timedelta(days=days_since_monday)
        
        for day in range(5):  # Monday to Friday (0-4)
            slot_date = monday + timedelta(days=day)
            if slot_date >= today:  # Only future dates
                # Check if slots are already booked
                time_7pm = time(19, 0)  # 7:00 PM
                time_8pm = time(20, 0)  # 8:00 PM
                
                slot_7pm_available = not ScheduledCourse.objects.filter(
                    skill_group="Private Lesson",
                    scheduled_date=slot_date,
                    scheduled_time=time_7pm,
                    is_active=True
                ).exists()
                
                slot_8pm_available = not ScheduledCourse.objects.filter(
                    skill_group="Private Lesson", 
                    scheduled_date=slot_date,
                    scheduled_time=time_8pm,
                    is_active=True
                ).exists()
                
                if slot_7pm_available:
                    available_slots.append({
                        'date': slot_date,
                        'time': time_7pm,
                        'date_str': slot_date.isoformat(),
                        'time_str': time_7pm.isoformat(),
                        'display': f"{slot_date.strftime('%A, %B %d, %Y')} - 7:00 PM - 8:00 PM"
                    })
                
                if slot_8pm_available:
                    available_slots.append({
                        'date': slot_date,
                        'time': time_8pm,
                        'date_str': slot_date.isoformat(),
                        'time_str': time_8pm.isoformat(),
                        'display': f"{slot_date.strftime('%A, %B %d, %Y')} - 8:00 PM - 9:00 PM"
                    })
    
    if request.method == 'POST':
        form = PrivateLessonForm(request.POST)
        
        # Get form data
        student_name = request.POST.get('student_name', '')
        student_age = request.POST.get('student_age', '')
        parent_name = request.POST.get('parent_name', '')
        contact_email = request.POST.get('contact_email', '')
        phone = request.POST.get('phone', '')
        experience_level = request.POST.get('experience_level', '')
        message = request.POST.get('message', '')
        selected_slot = request.POST.get('time_slot', '')
        
        if form.is_valid() and selected_slot:
            try:
                # Debug: Print the selected slot value
                print(f"DEBUG: Selected slot value: '{selected_slot}'")
                
                # Parse the selected slot
                slot_parts = selected_slot.split('|')
                print(f"DEBUG: Slot parts: {slot_parts}")
                
                if len(slot_parts) != 2:
                    raise ValueError(f"Invalid slot format: {slot_parts}")
                
                slot_date = date.fromisoformat(slot_parts[0])
                slot_time = time.fromisoformat(slot_parts[1])
                
                print(f"DEBUG: Parsed date: {slot_date}, time: {slot_time}")
                
                selected_skill = form.cleaned_data['skill']
                skill_display = selected_skill.split('|')[-1] if selected_skill else "General Skills"
                
                # Create instructor user (you might want to assign a specific instructor)
                instructor = request.user if request.user.is_authenticated and request.user.is_staff else None
                if not instructor:
                    # Get a default instructor or create one
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    instructor = User.objects.filter(is_staff=True).first()
                    if not instructor:
                        # Create a default private lesson instructor
                        instructor = User.objects.create_user(
                            username='private_instructor',
                            email='instructor@alt-project.com',
                            first_name='Private',
                            last_name='Instructor',
                            is_staff=True
                        )
                
                # Create the scheduled private lesson
                scheduled_lesson = ScheduledCourse.objects.create(
                    skill_group="Private Lesson",
                    skill_subgroup=skill_display,
                    skill_name=f"{student_name} ({experience_level})",
                    scheduled_date=slot_date,
                    scheduled_time=slot_time,
                    instructor=instructor,
                    max_students=1,  # Private lesson = 1 student max
                    is_active=True
                )
                
                # If user is authenticated, enroll them automatically
                if request.user.is_authenticated:
                    from .models import CourseAttendance
                    CourseAttendance.objects.create(
                        student=request.user,
                        scheduled_course=scheduled_lesson
                    )
                
                messages.success(request, 
                    f"Thank you {parent_name}! Your private lesson for {student_name} "
                    f"in {skill_display} has been scheduled for {slot_date.strftime('%A, %B %d, %Y')} "
                    f"from {slot_time.strftime('%I:%M %p')} to {(datetime.combine(slot_date, slot_time) + timedelta(hours=1)).strftime('%I:%M %p')}. "
                    f"We'll contact you at {contact_email} with additional details.")
                
                # Redirect to avoid re-submission on refresh
                return redirect('private_lesson')
            except (ValueError, IndexError) as e:
                print(f"DEBUG: Error parsing slot: {e}")
                messages.error(request, f"Invalid time slot selected: {e}. Please choose a valid time slot.")
        else:
            if not selected_slot:
                messages.error(request, "Please select a time slot for your private lesson.")
            else:
                print(f"DEBUG: Form errors: {form.errors}")
                print(f"DEBUG: Selected slot when form invalid: '{selected_slot}'")
                messages.error(request, "Please correct the errors below and try again.")
    else:
        form = PrivateLessonForm()
    
    return render(request, 'private_lesson.html', {
        'form': form, 
        'available_slots': available_slots
    })

def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validation
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'register.html')

        # Create user
        user = User.objects.create_user(username=username, password=password1)
        auth_login(request, user)

        messages.success(request, "Registration successful. You can now log in.")
        return redirect('index')

    return render(request, "register.html", {
        'show_navbar': False,
        'show_footer' : False
    })

def login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")        
            return redirect('profile')

def login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")        
            return redirect('profile')
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "login.html")
            
    return render(request, "login.html")

def logout(request):
    atuh_logout(request)
    messages.success(request, "You have been logged out.")
    return render(request, "index.html")

@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})

@login_required
def profile(request):
    user = request.user
    user_skills = user.skill.all().select_related('name__subgroup__group')
    
    # Organize skills by group and subgroup for better display
    organized_skills = {}
    for skill in user_skills:
        group = skill.group
        subgroup = skill.subgroup
        
        if group not in organized_skills:
            organized_skills[group] = {}
        if subgroup not in organized_skills[group]:
            organized_skills[group][subgroup] = []
        
        organized_skills[group][subgroup].append(skill)
    
    # Check if user has completed courses (for now, we'll use a simple check)
    # You can modify this logic based on your course completion tracking
    completed_courses = user_skills.filter(level__gte=80).count()  # Skills with 80+ level considered completed
    can_modify_skills = completed_courses > 0
    
    return render(request, 'profile.html', {
        'organized_skills': organized_skills,
        'user_skills': user_skills,
        'can_modify_skills': can_modify_skills,
        'completed_courses': completed_courses,
        'profile': user.profile if hasattr(user, 'profile') else None
    })

@login_required
def update_skill(request, skill_id):
    if request.method == "POST":
        action = request.POST.get("action")
        
        # Get the skill by ID instead of name to avoid conflicts
        skill = get_object_or_404(Skill, id=skill_id, user=request.user)
        
        # Increment or decrement
        if action == "increment":
            skill.level = min(skill.level + 1, 100)
        elif action == "decrement":
            skill.level = max(skill.level - 1, 0)
        
        skill.save()
        messages.success(request, f"Updated {skill.name.name} level to {skill.level}")
    
    return redirect("profile")

@login_required
def delete_skill(request, skill_id):
    if request.method == "POST":
        skill = get_object_or_404(Skill, id=skill_id, user=request.user)
        skill_name = skill.name.name
        skill.delete()
        messages.success(request, f"Removed {skill_name} from your skills")
    
    return redirect("profile")

@login_required
def add_skill(request):
    if request.method == 'POST':
        form = SkillForm(request.POST, user=request.user)
        if form.is_valid():
            # Parse the skill data from the form
            skill_key = form.cleaned_data['skill']
            level = form.cleaned_data['level']
            
            # Split the skill key to get group, subgroup, and skill name
            try:
                group, subgroup, skill_name = skill_key.split('|')
            except ValueError:
                messages.error(request, "Invalid skill selection.")
                return render(request, 'add_skill.html', {'form': form})
            
            # Get or create the required database objects
            from .models import SkillGroup, SkillSubgroup, SkillName
            
            # Get or create SkillGroup
            skill_group, created = SkillGroup.objects.get_or_create(name=group)
            
            # Get or create SkillSubgroup
            skill_subgroup, created = SkillSubgroup.objects.get_or_create(
                group=skill_group,
                name=subgroup
            )
            
            # Get or create SkillName
            skill_name_obj, created = SkillName.objects.get_or_create(
                subgroup=skill_subgroup,
                name=skill_name
            )
            
            # Create the user's skill
            skill = Skill.objects.create(
                name=skill_name_obj,
                group=group,
                subgroup=subgroup,
                user=request.user,
                level=level
            )
            
            messages.success(request, f"Successfully added {skill_name} with level {level}!")
            return redirect('profile')
    else:
        form = SkillForm(user=request.user)
    
    return render(request, 'add_skill.html', {'form': form})



@staff_member_required
def course_management(request):
    """Admin view to manage course enrollment requests"""
    # Get all pending requests
    pending_requests = CourseEnrollmentRequest.objects.filter(status='pending').order_by('-requested_at')
    
    # Get recent approved/rejected requests for reference
    recent_reviewed = CourseEnrollmentRequest.objects.filter(
        status__in=['approved', 'rejected']
    ).order_by('-reviewed_at')[:20]
    
    # Get statistics
    stats = {
        'pending_count': CourseEnrollmentRequest.objects.filter(status='pending').count(),
        'approved_count': CourseEnrollmentRequest.objects.filter(status='approved').count(),
        'rejected_count': CourseEnrollmentRequest.objects.filter(status='rejected').count(),
        'total_enrolled': ApprovedCourseEnrollment.objects.count(),
    }
    
    context = {
        'pending_requests': pending_requests,
        'recent_reviewed': recent_reviewed,
        'stats': stats,
    }
    
    return render(request, 'admin/course_management.html', context)

@staff_member_required
@require_http_methods(["POST"])
def process_enrollment_request(request, request_id):
    """Process (approve/reject) an enrollment request"""
    try:
        enrollment_request = get_object_or_404(CourseEnrollmentRequest, id=request_id, status='pending')
        data = json.loads(request.body)
        action = data.get('action')  # 'approve' or 'reject'
        admin_notes = data.get('notes', '')
        
        if action not in ['approve', 'reject']:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        # Update the request
        enrollment_request.status = 'approved' if action == 'approve' else 'rejected'
        enrollment_request.reviewed_at = timezone.now()
        enrollment_request.reviewed_by = request.user
        enrollment_request.admin_notes = admin_notes
        enrollment_request.save()
        
        # If approved, create the enrollment record
        if action == 'approve':
            ApprovedCourseEnrollment.objects.create(
                user=enrollment_request.user,
                skill_group=enrollment_request.skill_group,
                skill_subgroup=enrollment_request.skill_subgroup,
                skill_name=enrollment_request.skill_name,
                enrollment_request=enrollment_request
            )
        
        return JsonResponse({
            'success': True, 
            'message': f'Request {action}d successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def request_course_enrollment(request):
    """Handle course enrollment requests from users"""
    try:
        print(f"Received enrollment request from user: {request.user}")
        print(f"Request body: {request.body}")
        
        data = json.loads(request.body)
        skill_group = data.get('skill_group')
        skill_subgroup = data.get('skill_subgroup') 
        skill_name = data.get('skill_name')
        
        print(f"Parsed data - Group: {skill_group}, Subgroup: {skill_subgroup}, Skill: {skill_name}")
        
        if not all([skill_group, skill_subgroup, skill_name]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Check if user already has a request for this course
        existing_request = CourseEnrollmentRequest.objects.filter(
            user=request.user,
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                return JsonResponse({
                    'success': False, 
                    'error': 'You already have a pending request for this course'
                })
            elif existing_request.status == 'approved':
                return JsonResponse({
                    'success': False,
                    'error': 'You are already enrolled in this course'
                })
            elif existing_request.status == 'rejected':
                # Allow resubmission if previously rejected
                existing_request.status = 'pending'
                existing_request.requested_at = timezone.now()
                existing_request.reviewed_at = None
                existing_request.reviewed_by = None
                existing_request.admin_notes = ''
                existing_request.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Your enrollment request has been resubmitted for review'
                })
        else:
            # Create new request
            CourseEnrollmentRequest.objects.create(
                user=request.user,
                skill_group=skill_group,
                skill_subgroup=skill_subgroup,
                skill_name=skill_name
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Your enrollment request has been submitted for admin approval'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def check_course_enrollment_status(request):
    """Check if user is enrolled in a specific course"""
    skill_group = request.GET.get('skill_group')
    skill_subgroup = request.GET.get('skill_subgroup')
    skill_name = request.GET.get('skill_name')
    
    if not all([skill_group, skill_subgroup, skill_name]):
        return JsonResponse({'enrolled': False, 'status': 'missing_params'})
    
    # Check if approved enrollment exists
    enrollment = ApprovedCourseEnrollment.objects.filter(
        user=request.user,
        skill_group=skill_group,
        skill_subgroup=skill_subgroup,
        skill_name=skill_name
    ).first()
    
    if enrollment:
        return JsonResponse({'enrolled': True, 'status': 'approved'})
    
    # Check if there's a pending request
    pending_request = CourseEnrollmentRequest.objects.filter(
        user=request.user,
        skill_group=skill_group,
        skill_subgroup=skill_subgroup,
        skill_name=skill_name,
        status='pending'
    ).first()
    
    if pending_request:
        return JsonResponse({'enrolled': False, 'status': 'pending'})
    
    # Check if there's a rejected request
    rejected_request = CourseEnrollmentRequest.objects.filter(
        user=request.user,
        skill_group=skill_group,
        skill_subgroup=skill_subgroup,
        skill_name=skill_name,
        status='rejected'
    ).first()
    
    if rejected_request:
        return JsonResponse({
            'enrolled': False, 
            'status': 'rejected',
            'rejection_reason': rejected_request.admin_notes or 'No specific reason provided.'
        })
    
    return JsonResponse({'enrolled': False, 'status': 'not_requested'})

def debug_enrollment(request):
    """Debug endpoint to test enrollment system"""
    if request.method == 'GET':
        return JsonResponse({
            'user': request.user.username if request.user.is_authenticated else 'Anonymous',
            'is_authenticated': request.user.is_authenticated,
            'total_requests': CourseEnrollmentRequest.objects.count(),
            'user_requests': CourseEnrollmentRequest.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
        })

@staff_member_required
@require_http_methods(["POST"])
def schedule_course(request):
    """Schedule an approved course for a specific date and time"""
    try:
        data = json.loads(request.body)
        skill_group = data.get('skill_group')
        skill_subgroup = data.get('skill_subgroup')
        skill_name = data.get('skill_name')
        scheduled_date = data.get('date')  # Changed from 'scheduled_date' to 'date'
        scheduled_time = data.get('time')  # Changed from 'scheduled_time' to 'time'
        max_students = data.get('max_students', 20)
        
        if not all([skill_group, skill_subgroup, skill_name, scheduled_date, scheduled_time]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Check if this course is already scheduled for this date/time
        existing_schedule = ScheduledCourse.objects.filter(
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time
        ).first()
        
        if existing_schedule:
            return JsonResponse({
                'success': False,
                'error': 'This course is already scheduled for this date and time'
            })
        
        # Create the scheduled course
        scheduled_course = ScheduledCourse.objects.create(
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            instructor=request.user,
            max_students=max_students
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Course scheduled successfully for {scheduled_date} at {scheduled_time}',
            'course_id': scheduled_course.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

