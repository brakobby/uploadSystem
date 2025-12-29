from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import *
from django.http import HttpResponse

# Create your views here.

def registerView(request):
    if request.method =='POST':
        full_name = request.POST['fullname']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if(password!=confirm_password):
            messages.error(request, "Password not match")
            return redirect('register')
        
        if(Registration.objects.filter(username = username)):
            messages.error(request,"Username already exists")
            return redirect('register')
        
        if(Registration.objects.filter(email = email)):
            messages.error(request, "Email has already been used")
            return redirect('register')
        
        hashed_password = make_password(password)

        Registration.objects.create(
            fullname = full_name,
            username = username,
            email = email,
            password = hashed_password
        )

        messages.success(request, f"{full_name} has been registered successfully")
        return redirect('login')

    return render(request, 'accounts/register.html')

def loginView(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            user = Registration.objects.get(username = username)
            if(check_password(password, user.password)):
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                messages.success(request, "Login Successful")
                return redirect('upload')
            
            else:
                messages.error(request,"Incorrect Password")
                return redirect('login')

        except Registration.DoesNotExist:
            messages.error(request, "User does not exist")

    return render(request, 'accounts/login.html')



def uploadView(request):
    return render(request, 'mainpages/upload.html')

def adminReg(request):
    return render(request, 'adminPortal/admin-register.html')

def adminLoginView(request):
    if request.method == 'POST':
        username = request.POST.get('admin_username')
        password = request.POST.get('admin_password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, f"Welcome, Admin {user.username}")
            return redirect('admin_dashboard')
        elif user is not None and not user.is_superuser:
            messages.error(request, "Access denied: not an admin user.")
            return redirect('admin_login')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('admin_login')

    return render(request, 'adminPortal/login-admin.html')

@login_required(login_url='admin_login')
def adminDashboardView(request):
    if not request.user.is_superuser:
        return redirect('admin_login')
    # Your dashboard logic here
    return render(request, 'adminPortal/admin.html')


def adminLogoutView(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('admin_login')

