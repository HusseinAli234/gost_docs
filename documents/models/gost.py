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
    report_type = models.CharField(max_length=20, choices=[('final', 'Заключительный'), ('intermediate', 'Промежуточный')],default=('intermediate', 'Промежуточный'))
    year = models.PositiveIntegerField(default=2024)
    created_at = models.DateTimeField(auto_now_add=True)

    # Связи на другие части отчета
    introduction = RichTextField(blank=True, null=True)
    main_part = RichTextField(blank=True, null=True)
    conclusion = RichTextField(blank=True, null=True)

    def __str__(self):
        return self.title


class TitlePage(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='title_page')
    stage_name = models.CharField(max_length=255, blank=True)
    udk = models.CharField(max_length=50, blank=True)
    registration_number_nioktr = models.CharField(max_length=100, blank=True)
    registration_number_ikrbs = models.CharField(max_length=100, blank=True)
    program_code = models.CharField(max_length=255, blank=True)
    book_number = models.CharField(max_length=20, blank=True)
    federal_program_name = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    head_full_name = models.CharField(max_length=255, blank=True)
    head_position = models.CharField(max_length=255, blank=True)
    head_degree = models.CharField(max_length=100, blank=True)
    approval_date = models.DateField(blank=True, null=True)


class Performer(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='performers')
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    degree = models.CharField(max_length=100)
    participation = models.CharField(max_length=500, blank=True)
    signed = models.BooleanField(default=False)
    date_signed = models.DateField(blank=True, null=True)


class Abstract(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='abstract')
    content = RichTextField()


class Term(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='terms')
    term = models.CharField(max_length=255)
    definition = models.TextField()


class Abbreviation(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='abbreviations')
    abbreviation = models.CharField(max_length=100)
    meaning = models.TextField()


class Reference(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='references')
    citation = models.TextField()
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']


class Appendix(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='appendices')
    label = models.CharField(max_length=10)  # Пример: А, Б, В
    title = models.CharField(max_length=255)
    content = RichTextField()
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
