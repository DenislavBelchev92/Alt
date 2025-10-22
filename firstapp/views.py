from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Skill, SkillName, CourseEnrollmentRequest, ApprovedCourseEnrollment
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
    message = "Hello"
    extra_message = "^_^"
    return render(request, 'index.html', {\
        'message': message,
        'extra_message': extra_message})

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
        preferred_day = request.POST.get('preferred_day', '')
        preferred_time = request.POST.get('preferred_time', '')
        
        if form.is_valid():
            selected_skill = form.cleaned_data['skill']
            
            # Here you could save to database, send email, etc.
            # For now, just show a success message
            
            skill_display = selected_skill.split('|')[-1] if selected_skill else "Selected Skill"
            
            messages.success(request, 
                f"Thank you {parent_name}! We've received your private lesson request for {student_name} "
                f"in {skill_display}. We'll contact you at {contact_email} within 24 hours to schedule the lesson.")
            
            # Redirect to avoid re-submission on refresh
            return redirect('private_lesson')
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = PrivateLessonForm()
    
    return render(request, 'private_lesson.html', {'form': form})

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
        messages.success(request, f"Updated {skill_name} level to {level}")
    
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

