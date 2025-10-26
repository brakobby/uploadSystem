from django.db import models

# Create your models here.

class Registration(models.Model):
    fullname = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255)
    password = models.CharField(255)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
    
class FileUpload(models.Model):
    user = models.ForeignKey(Registration, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=255)
    project_description = models.CharField(max_length=300)
    file = models.FileField(upload_to='uploads/')
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project_title}-{self.user.username}"

