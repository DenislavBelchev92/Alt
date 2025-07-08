from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as atuh_logout
from django.contrib import messages
from django.shortcuts import render, redirect

def index(request):
    message = "Hello"
    extra_message = "try 1"
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
            return render(request, 'index.html', {\
                'show_navbar' : True,
                'show_footer' : True
            })
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
    extra_message = "DDD"
    return render(request, 'profile.html', {\
        'message': message,
        'extra_message': extra_message})
