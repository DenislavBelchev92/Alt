from django.shortcuts import render

def index(request):
    message = "Hello"
    extra_message = "try 1"
    return render(request, 'index.html', {\
        'message': message,
        'extra_message': extra_message})

def login(request):
    return render(request, 'login.html', {\
        'show_footer' : False
    })