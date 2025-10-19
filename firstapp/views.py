from django.shortcuts import render
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Skill, SkillName 
from .forms import SkillForm, ProfileForm
import yaml
import os
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
        return redirect('login')

    return render(request, 'register.html', {\
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
            return redirect('profile_skills')
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
            return redirect('profile_skills')  # assuming 'profile' is your profile view name
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})

@login_required
def profile_skills(request):
    user_skills = request.user.skill.all().select_related('name__subgroup__group')
    
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
    
    return render(request, 'profile_skills.html', {
        'organized_skills': organized_skills,
        'user_skills': user_skills
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
    
    return redirect("profile_skills")

@login_required
def delete_skill(request, skill_id):
    if request.method == "POST":
        skill = get_object_or_404(Skill, id=skill_id, user=request.user)
        skill_name = skill.name.name
        skill.delete()
        messages.success(request, f"Removed {skill_name} from your skills")
    
    return redirect("profile_skills")

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
            return redirect('profile_skills')
    else:
        form = SkillForm(user=request.user)
    
    return render(request, 'add_skill.html', {'form': form})

