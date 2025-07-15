from django.shortcuts import render
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Skill, SkillName 
from .forms import SkillForm, ProfileForm

User = get_user_model()

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
    message = "Skills Profile Page"
    return render(request, 'profile_skills.html', {\
        'message': message})

@login_required
def update_skill(request, skill_name):
    if request.method == "POST":
        action = request.POST.get("action")

        # Get the SkillName object by its name (assuming skill_name is a string)
        skill_name_obj = get_object_or_404(SkillName, name=skill_name)

        # Find the Skill object for this user and skill name
        skill = get_object_or_404(Skill, user=request.user, name=skill_name_obj)

        # Increment or decrement
        if action == "increment":
            skill.level = min(skill.level + 1, 100)
        elif action == "decrement":
            skill.level = max(skill.level - 1, 0)

        skill.save()
    return redirect("profile_skills")

def add_skill(request):
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('profile_skills')
    else:
        form = SkillForm()
    return render(request, 'add_skill.html', {'form': form})

