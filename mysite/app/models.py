from django.db import models

# Create your models here.
class Alert(models.Model):
    ip_source = models.CharField(max_length=30)
    ip_destination = models.CharField(max_length=30)
    port = models.CharField(max_length=30)
    agent = models.CharField(max_length=30)
    datasource = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Status(models.Model):
    status = models.BooleanField(default=False)