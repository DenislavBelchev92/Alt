from django.shortcuts import render
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Skill
from .forms import SkillForm

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
            return redirect('profile')
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "login.html")
            
    return render(request, "login.html")

def logout(request):
    atuh_logout(request)
    messages.success(request, "You have been logged out.")
    return render(request, "index.html")

def profile(request):
    message = "Profile Page"
    return render(request, 'profile.html', {\
        'message': message,
        'skills':request.user.get_skills()})

@login_required
def update_skill(request, skill_name):
    if request.method == "POST":
        action = request.POST.get("action")
        skill = get_object_or_404(Skill, user=request.user, name=skill_name)
        # Increment or decrement
        if action == "increment":
            skill.rate = min(skill.rate + 10, 100)  # you may adjust step
        elif action == "decrement":
            skill.rate = max(skill.rate - 10, 0)

        skill.save()
    return redirect("profile")  # Or wherever you want to go

def add_skill(request):
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user  # Associate the skill with the current user
            skill.save()
            return redirect('profile')  # Change to your profile or skills list page
    else:
        form = SkillForm()
    return render(request, 'add_skill.html', {'form': form})