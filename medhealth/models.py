from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('owner', 'Владелец клиники'),
        ('admin', 'Администратор'),
        ('doctor', 'Врач'),
        ('manager', 'Менеджер'),
        ('patient', 'Пациент'),
    )
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=120, null=True, blank=True)
    last_name = models.CharField(max_length=120, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password_user = models.CharField(max_length=128, null=True, blank=True)

    USERNAME_FIELD = 'email'
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=17)
    date_of_birth = models.DateField()
    address = models.TextField()

    REQUIRED_FIELDS = ['first_name', 'last_name', 'role', 'phone_number', 'date_of_birth', 'address']

    groups = models.ManyToManyField('auth.Group', verbose_name='groups', blank=True, related_name='customuser_set')
    user_permissions = models.ManyToManyField('auth.Permission', verbose_name='user permissions', blank=True, related_name='customuser_set')

    class Meta:
        db_table = 'custom_user'

class Admin(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    class Meta:
        db_table = 'admins'

class Requests(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    name_clinic = models.CharField(max_length=120)
    email = models.EmailField()
    phone_number = models.CharField(max_length=120)
    description = models.TextField()
    class Meta:
        db_table = 'requests'

class ClinicOwner(models.Model):
    id = models.AutoField(primary_key=True)
    name_clinic = models.CharField(max_length=200)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    class Meta:
        db_table = 'clinic_owners'

class Branch(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.TextField()
    description = models.TextField(null=True, blank=True)
    working_hours = models.CharField(max_length=100, default="")
    off_days = models.CharField(max_length=100, default="")
    clinic_owner = models.ForeignKey(ClinicOwner, on_delete=models.CASCADE)
    class Meta:
        db_table = 'branches'

class Manager(models.Model):
    id = models.AutoField(primary_key=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='managers')
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    class Meta:
        db_table = 'managers'

class Doctor(models.Model):
    GENDER_CHOICES = (('male', 'Мужской'), ('female', 'Женский'))
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=150, default="Терапевт")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    age = models.PositiveIntegerField(default=25)
    photo = models.ImageField(upload_to='doctors_photos/', null=True, blank=True)
    education = models.TextField()
    experience_years = models.PositiveIntegerField()
    description = models.TextField()
    working_hours = models.CharField(max_length=100, default="")
    off_days = models.CharField(max_length=100, default="")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='doctors')
    class Meta:
        db_table = 'doctors'

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Запланирован'),
        ('completed', 'Завершен'),
        ('no_show', 'Не пришел'),
        ('cancelled', 'Отменен'),
    )
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')

    symptomsDescribedByPatient = models.TextField(blank=True, default='')

    selfTreatmentMethodsTaken = models.TextField(blank=True, default='')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appointments'
        unique_together = ('doctor', 'date', 'time')