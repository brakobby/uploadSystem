from django.shortcuts import render, redirect, get_object_or_404
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
    if 'user_id' not in request.session:
        messages.error(request, "Please login first.")
        return redirect('login')
    
    user = Registration.objects.get(id=request.session['user_id'])

    if request.method =='POST':
        title = request.POST['title']
        description = request.POST['description']
        file = request.FILES['file']

        if not (title and description and file):
            messages.error(request, "Please fill in all fields.")
            return redirect('upload')
        
        FileUpload.objects.create(
            user = user,
            project_title = title,
            project_description = description,
            file = file
        )
        messages.success(request, "Project uploaded successfully.")
        return redirect('upload')
    
    projects = FileUpload.objects.filter(user=user).order_by('-date_added')
    return render(request, 'mainpages/upload.html', {'projects': projects})



def LogoutView(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

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
    
    projects = FileUpload.objects.all().order_by('-date_added')
    total_projects = projects.count()
    total_students = len(set(projects.values_list('user', flat=True)))
    pending_reviews = projects.filter(grade__isnull = True).count()
    submission_rate = (total_projects/total_students * 100) if total_students else 0


    query = request.GET.get('q')
    if query:
        students = FileUpload.objects.filter(
            user__fullname__icontains=query
        ).order_by('user__fullname')
    
    else:
        students = FileUpload.objects.all().order_by('user__fullname')
   
    context = {
        'projects': projects,
        'students': students,
        'query':query,
        'total_projects': total_projects,
        'total_students': total_students,
        'pending_reviews': pending_reviews,
        'submission_rate': round(submission_rate,1), 
    }


    return render(request, 'adminPortal/admin.html', context)


def adminLogoutView(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('admin_login')

@login_required(login_url='admin_login')
def delete_project(request, pk):
    project = get_object_or_404(FileUpload, id=pk)
    project.delete()
    return redirect('admin_dashboard')


@login_required(login_url='admin-login')
def grade_project(request, pk):
    project = get_object_or_404(FileUpload, id = pk)

    if request.method == 'POST':
        grade = request.POST['grade']
        feedback = request.POST['feedback']
        project.grade = grade
        project.feedback = feedback
        project.save()
        messages.success(request, f"Grade '{grade}' assigned to {project.project_title}")
        return redirect('admin_dashboard')
    
    return render(request, 'adminPortal/grade_project.html', {'project': project})