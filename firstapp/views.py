from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Skill, SkillName, CourseEnrollmentRequest, ApprovedCourseEnrollment, ScheduledCourse, CourseAttendance, MAX_PARTICIPANTS_PER_COURSE
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
    
    # Get users who are already enrolled in scheduled courses to exclude their requests
    enrolled_users = CourseAttendance.objects.all().values_list(
        'student_id', 'scheduled_course__skill_group', 'scheduled_course__skill_subgroup', 'scheduled_course__skill_name'
    )
    enrolled_user_courses = set(enrolled_users)
    
    # Create combined schedule courses data (exclude only users already enrolled in sessions)
    schedule_courses_data = []
    
    # Add pending requests to schedule courses (exclude users already enrolled in sessions)
    for enrollment_request in pending_requests:
        user_course_key = (
            enrollment_request.user.id, 
            enrollment_request.skill_group, 
            enrollment_request.skill_subgroup, 
            enrollment_request.skill_name
        )
        if user_course_key not in enrolled_user_courses:
            schedule_courses_data.append({
                'type': 'pending',
                'request_id': enrollment_request.id,
                'student': enrollment_request.user,
                'course_full_name': f"{enrollment_request.skill_group} > {enrollment_request.skill_subgroup} > {enrollment_request.skill_name}",
                'skill_group': enrollment_request.skill_group,
                'skill_subgroup': enrollment_request.skill_subgroup,
                'skill_name': enrollment_request.skill_name,
                'requested_at': enrollment_request.requested_at,
                'status': 'pending'
            })
    
    # Sort by requested date (newest first)
    schedule_courses_data.sort(key=lambda x: x['requested_at'], reverse=True)
    
    # Get scheduled courses with participants
    scheduled_courses_data = []
    scheduled_courses = ScheduledCourse.objects.all().order_by('-scheduled_date', '-scheduled_time')
    
    for course in scheduled_courses:
        # Get participants for this course
        participants = CourseAttendance.objects.filter(scheduled_course=course).select_related('student')
        
        # Show ALL scheduled courses, including empty ones
        scheduled_courses_data.append({
            'id': course.id,
            'skill_group': course.skill_group,
            'skill_subgroup': course.skill_subgroup,
            'skill_name': course.skill_name,
            'course_full_name': f"{course.skill_group} > {course.skill_subgroup} > {course.skill_name}",
            'scheduled_date': course.scheduled_date,
                'scheduled_time': course.scheduled_time,
                'instructor': course.instructor,
                'max_students': course.max_students,
                'participants': participants,
                'enrolled_count': participants.count(),
                'available_spots': course.max_students - participants.count()
            })
    
    # Get statistics
    unique_courses = set()
    for item in schedule_courses_data:
        if item['status'] == 'approved':
            course_key = f"{item['skill_group']}|{item['skill_subgroup']}|{item['skill_name']}"
            unique_courses.add(course_key)
    
    stats = {
        'pending_count': CourseEnrollmentRequest.objects.filter(status='pending').count(),
        'approved_count': CourseEnrollmentRequest.objects.filter(status='approved').count(),
        'rejected_count': CourseEnrollmentRequest.objects.filter(status='rejected').count(),
        'total_enrolled': ApprovedCourseEnrollment.objects.count(),
        'unique_courses': len(unique_courses),
        'scheduled_courses_count': len(scheduled_courses_data),
    }
    
    context = {
        'schedule_courses': schedule_courses_data,
        'recent_reviewed': recent_reviewed,
        'scheduled_courses': scheduled_courses_data,
        'stats': stats,
        'MAX_PARTICIPANTS': MAX_PARTICIPANTS_PER_COURSE,
    }
    
    return render(request, 'admin/course_management.html', context)

@staff_member_required
@require_http_methods(["POST"])
def process_enrollment_request(request, request_id):
    """Process (reject) an enrollment request"""
    try:
        enrollment_request = get_object_or_404(CourseEnrollmentRequest, id=request_id, status='pending')
        data = json.loads(request.body)
        action = data.get('action')
        admin_notes = data.get('notes', '')
        
        if action != 'reject':
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        # Update the request
        enrollment_request.status = 'rejected'
        enrollment_request.reviewed_at = timezone.now()
        enrollment_request.reviewed_by = request.user
        enrollment_request.admin_notes = admin_notes
        enrollment_request.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Request rejected successfully'
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
        
        # Prevent admin users from creating enrollment requests via the public endpoint
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            return JsonResponse({'success': False, 'error': 'Administrators cannot submit enrollment requests.'})

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
    """Schedule a specific enrollment request for a specific date and time"""
    try:
        data = json.loads(request.body)
        skill_group = data.get('skill_group')
        skill_subgroup = data.get('skill_subgroup')
        skill_name = data.get('skill_name')
        request_id = data.get('request_id')  # Specific enrollment request ID
        scheduled_date = data.get('date')  # Changed from 'scheduled_date' to 'date'
        scheduled_time = data.get('time')  # Changed from 'scheduled_time' to 'time'
        max_students = data.get('max_students', 20)
        
        if not all([skill_group, skill_subgroup, skill_name, request_id, scheduled_date, scheduled_time]):
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
        
        # Get the specific enrollment request
        try:
            participant_request = CourseEnrollmentRequest.objects.get(
                id=request_id,
                skill_group=skill_group,
                skill_subgroup=skill_subgroup,
                skill_name=skill_name,
                status='pending'
            )
        except CourseEnrollmentRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Enrollment request not found or already processed'})
        
        # Check if this participant is already enrolled in ANY session for this course
        existing_enrollment = CourseAttendance.objects.filter(
            student=participant_request.user,
            scheduled_course__skill_group=skill_group,
            scheduled_course__skill_subgroup=skill_subgroup,
            scheduled_course__skill_name=skill_name
        ).exists()
        
        if existing_enrollment:
            return JsonResponse({'success': False, 'error': f'User {participant_request.user.username} is already enrolled in a session for this course'})
        
        # Enroll the specific user
        # Auto-approve the enrollment request
        participant_request.status = 'approved'
        participant_request.reviewed_at = timezone.now()
        participant_request.reviewed_by = request.user
        participant_request.admin_notes = f'Approved when scheduling course on {scheduled_date} at {scheduled_time}'
        participant_request.save()
        
        # Create the approved enrollment record
        ApprovedCourseEnrollment.objects.create(
            user=participant_request.user,
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name,
            enrollment_request=participant_request
        )
        
        # Enroll in the scheduled course
        CourseAttendance.objects.create(
            student=participant_request.user,
            scheduled_course=scheduled_course,
            attended=False
        )
        enrolled_count = 1
        
        return JsonResponse({
            'success': True,
            'message': f'Course scheduled successfully for {participant_request.user.username} on {scheduled_date} at {scheduled_time}.',
            'course_id': scheduled_course.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def reschedule_course(request, course_id):
    """Reschedule an existing course to a new date and time"""
    try:
        scheduled_course = get_object_or_404(ScheduledCourse, id=course_id)
        data = json.loads(request.body)
        new_date = data.get('date')
        new_time = data.get('time')
        
        if not all([new_date, new_time]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Check if there's already a course scheduled for this date/time with the same skill
        existing_schedule = ScheduledCourse.objects.filter(
            skill_group=scheduled_course.skill_group,
            skill_subgroup=scheduled_course.skill_subgroup,
            skill_name=scheduled_course.skill_name,
            scheduled_date=new_date,
            scheduled_time=new_time
        ).exclude(id=course_id).first()
        
        if existing_schedule:
            return JsonResponse({
                'success': False,
                'error': 'This course is already scheduled for this date and time'
            })
        
        # Store old schedule for the message
        old_date = scheduled_course.scheduled_date
        old_time = scheduled_course.scheduled_time
        
        # Update the scheduled course
        scheduled_course.scheduled_date = new_date
        scheduled_course.scheduled_time = new_time
        scheduled_course.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Course rescheduled from {old_date} {old_time} to {new_date} {new_time}',
            'course_id': scheduled_course.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def dismiss_course(request, course_id):
    """Dismiss a scheduled course and revert all enrolled students back to pending status"""
    try:
        scheduled_course = get_object_or_404(ScheduledCourse, id=course_id)
        
        # Get all enrolled students for this course
        enrolled_students = CourseAttendance.objects.filter(scheduled_course=scheduled_course)
        
        # Store course info for the message
        course_name = f"{scheduled_course.skill_group} > {scheduled_course.skill_subgroup} > {scheduled_course.skill_name}"
        enrolled_count = enrolled_students.count()
        
        # Revert all enrolled students back to pending status
        for attendance in enrolled_students:
            # Find the corresponding enrollment request and revert it to pending
            try:
                enrollment_request = CourseEnrollmentRequest.objects.get(
                    user=attendance.student,
                    skill_group=scheduled_course.skill_group,
                    skill_subgroup=scheduled_course.skill_subgroup,
                    skill_name=scheduled_course.skill_name,
                    status='approved'
                )
                
                # Revert to pending status
                enrollment_request.status = 'pending'
                enrollment_request.reviewed_at = None
                enrollment_request.reviewed_by = None
                enrollment_request.admin_notes = f'Course dismissed on {timezone.now().strftime("%Y-%m-%d at %H:%M")}. Reverted to pending status.'
                enrollment_request.save()
                
                # Delete the approved enrollment record
                ApprovedCourseEnrollment.objects.filter(
                    user=attendance.student,
                    skill_group=scheduled_course.skill_group,
                    skill_subgroup=scheduled_course.skill_subgroup,
                    skill_name=scheduled_course.skill_name
                ).delete()
                
            except CourseEnrollmentRequest.DoesNotExist:
                # If no enrollment request found, create one in pending status
                CourseEnrollmentRequest.objects.create(
                    user=attendance.student,
                    skill_group=scheduled_course.skill_group,
                    skill_subgroup=scheduled_course.skill_subgroup,
                    skill_name=scheduled_course.skill_name,
                    status='pending',
                    admin_notes=f'Course dismissed on {timezone.now().strftime("%Y-%m-%d at %H:%M")}. Created pending request.'
                )
        
        # Delete all course attendance records
        enrolled_students.delete()
        
        # Delete the scheduled course
        scheduled_course.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Course "{course_name}" was dismissed. {enrolled_count} students reverted to pending status and will appear in Schedule Courses.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
def course_detail(request, skill_group, skill_subgroup, skill_name):
    """Admin-only view to show detailed course information with upcoming dates and participants"""
    
    # Get all approved participants for this course
    participants = ApprovedCourseEnrollment.get_course_participants(skill_group, skill_subgroup, skill_name)
    participant_count = participants.count()
    available_spots = ApprovedCourseEnrollment.get_available_spots(skill_group, skill_subgroup, skill_name)
    
    # Get upcoming scheduled courses for this skill
    upcoming_courses = ScheduledCourse.objects.filter(
        skill_group=skill_group,
        skill_subgroup=skill_subgroup,
        skill_name=skill_name,
        scheduled_date__gte=timezone.now().date()
    ).order_by('scheduled_date', 'scheduled_time')
    
    # For each scheduled course, get the attendance records
    courses_with_attendance = []
    for course in upcoming_courses:
        attendees = CourseAttendance.objects.filter(
            scheduled_course=course
        ).select_related('student')
        
        courses_with_attendance.append({
            'course': course,
            'attendees': attendees,
            'enrolled_count': attendees.count(),
            'available_spots': course.max_students - attendees.count()
        })
    
    course_name = f"{skill_group} > {skill_subgroup} > {skill_name}"
    
    context = {
        'skill_group': skill_group,
        'skill_subgroup': skill_subgroup,
        'skill_name': skill_name,
        'course_name': course_name,
        'participants': participants,
        'participant_count': participant_count,
        'available_spots': available_spots,
        'max_participants': MAX_PARTICIPANTS_PER_COURSE,
        'upcoming_courses': courses_with_attendance,
        'has_upcoming_courses': len(courses_with_attendance) > 0,
        'today': timezone.now().date(),
    }
    
    return render(request, 'course_detail.html', context)

@staff_member_required
def get_existing_sessions(request):
    """Get existing scheduled sessions for a specific course"""
    skill_group = request.GET.get('skill_group')
    skill_subgroup = request.GET.get('skill_subgroup')
    skill_name = request.GET.get('skill_name')
    
    if not all([skill_group, skill_subgroup, skill_name]):
        return JsonResponse({'success': False, 'error': 'Missing required parameters'})
    
    # Get existing scheduled courses for this skill
    scheduled_courses = ScheduledCourse.objects.filter(
        skill_group=skill_group,
        skill_subgroup=skill_subgroup,
        skill_name=skill_name,
        scheduled_date__gte=timezone.now().date()  # Only future sessions
    ).order_by('scheduled_date', 'scheduled_time')
    
    sessions = []
    for course in scheduled_courses:
        enrolled_count = CourseAttendance.objects.filter(scheduled_course=course).count()
        available_spots = course.max_students - enrolled_count
        
        # Only include sessions that have available spots
        if available_spots > 0:
            sessions.append({
                'id': course.id,
                'date': course.scheduled_date.strftime('%Y-%m-%d'),
                'time': course.scheduled_time.strftime('%H:%M'),
                'enrolled': enrolled_count,
                'max_students': course.max_students,
                'available_spots': available_spots
            })
    
    return JsonResponse({
        'success': True,
        'sessions': sessions
    })

@staff_member_required  
@require_http_methods(["POST"])
def add_to_existing_session(request):
    """Add all pending participants to an existing scheduled session"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        skill_group = data.get('skill_group')
        skill_subgroup = data.get('skill_subgroup')
        skill_name = data.get('skill_name')
        
        if not all([session_id, skill_group, skill_subgroup, skill_name]):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Get the scheduled course
        try:
            scheduled_course = ScheduledCourse.objects.get(id=session_id)
        except ScheduledCourse.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scheduled course not found'})
        
        # Get pending enrollment requests for this course type
        pending_participants = CourseEnrollmentRequest.objects.filter(
            skill_group=skill_group,
            skill_subgroup=skill_subgroup,
            skill_name=skill_name,
            status='pending'
        )
        
        # Get already enrolled participants for this course type (any session)
        already_enrolled = CourseAttendance.objects.filter(
            scheduled_course__skill_group=skill_group,
            scheduled_course__skill_subgroup=skill_subgroup,
            scheduled_course__skill_name=skill_name
        ).values_list('student_id', flat=True)
        
        # Filter out already enrolled participants
        new_participants = pending_participants.exclude(user_id__in=already_enrolled)
        
        if not new_participants.exists():
            return JsonResponse({
                'success': False, 
                'error': 'No new participants to add. All pending participants are already enrolled in a session for this course.'
            })
        
        # Check if there's enough space in this specific session
        current_enrolled_in_session = CourseAttendance.objects.filter(
            scheduled_course=scheduled_course
        ).count()
        new_count = new_participants.count()
        
        if current_enrolled_in_session + new_count > scheduled_course.max_students:
            available_spots = scheduled_course.max_students - current_enrolled_in_session
            return JsonResponse({
                'success': False,
                'error': f'Not enough space. Only {available_spots} spots available, but trying to add {new_count} participants.'
            })
        
        # Enroll new participants (auto-approve and enroll)
        enrolled_count = 0
        for participant_request in new_participants:
            # Auto-approve the enrollment request
            participant_request.status = 'approved'
            participant_request.reviewed_at = timezone.now()
            participant_request.reviewed_by = request.user
            participant_request.admin_notes = f'Auto-approved when adding to existing session on {scheduled_course.scheduled_date} at {scheduled_course.scheduled_time}'
            participant_request.save()
            
            # Create the approved enrollment record
            ApprovedCourseEnrollment.objects.create(
                user=participant_request.user,
                skill_group=skill_group,
                skill_subgroup=skill_subgroup,
                skill_name=skill_name,
                enrollment_request=participant_request
            )
            
            # Enroll in the scheduled course
            CourseAttendance.objects.create(
                student=participant_request.user,
                scheduled_course=scheduled_course,
                attended=False
            )
            enrolled_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully added {enrolled_count} participants to the session on {scheduled_course.scheduled_date} at {scheduled_course.scheduled_time}.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Google Drive Integration Views

@login_required
def get_gdrive_resource(request):
    """API endpoint to get Google Drive resource URL"""
    try:
        from .gdrive import get_gdrive_resource as get_resource, get_auth_url
        
        resource_name = request.GET.get('resource')
        folder_path = request.GET.get('folder', 'Alt')  # Default to Alt folder
        
        if not resource_name:
            return JsonResponse({'success': False, 'error': 'Resource name required'})
        
        result = get_resource(request.user.id, resource_name, folder_path)
        
        # If authentication required, generate auth URL
        if not result['success'] and result.get('auth_required'):
            # Check if this is a retry request (force reset for scope issues)
            force_reset = request.GET.get('reset_auth') == 'true'
            auth_url = get_auth_url(request, request.user.id, force_reset=force_reset)
            if auth_url:
                result['auth_url'] = auth_url
        

        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def oauth2callback(request):
    """Handle Google OAuth callback"""
    try:
        from .gdrive import handle_oauth_callback
        
        if 'error' in request.GET:
            return render(request, 'oauth_error.html', {
                'error': request.GET.get('error'),
                'error_description': request.GET.get('error_description', 'OAuth authorization failed')
            })
        
        success = handle_oauth_callback(request)
        
        if success:
            return render(request, 'oauth_success.html', {
                'message': 'Google Drive access authorized successfully! You can now close this window.'
            })
        else:
            return render(request, 'oauth_error.html', {
                'error': 'OAuth Error',
                'error_description': 'Failed to complete authorization'
            })
            
    except Exception as e:
        return render(request, 'oauth_error.html', {
            'error': 'System Error',
            'error_description': str(e)
        })
