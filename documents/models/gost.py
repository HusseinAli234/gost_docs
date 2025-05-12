from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField

class Document(models.Model):
    TEMPLATE_CHOICES = [
        ('gost', 'ГОСТ 7.32'),
        ('sto', 'СТО СФУ 4.2'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    template_type = models.CharField(max_length=10, choices=TEMPLATE_CHOICES)
    introduction = RichTextField(blank=True, null=True)
    goal = RichTextField(blank=True, null=True)
    tasks = RichTextField(blank=True, null=True)
    main_part = RichTextField(blank=True, null=True)
    conclusion = RichTextField(blank=True, null=True)
    year = models.PositiveIntegerField(default=2024)
    department = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=255, blank=True)
    doc_type = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
