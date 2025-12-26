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

    # 1. ПЕРЕОПРЕДЕЛЕНИЕ: Делаем username необязательным
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True
    )

    first_name = models.CharField(max_length=120, null=True, blank=True)
    last_name = models.CharField(max_length=120, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password_user = models.CharField(max_length=128, null=True, blank=True)

    # 2. Поле для логина
    USERNAME_FIELD = 'email'

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )
    phone_number = models.CharField(max_length=17)
    date_of_birth = models.DateField()
    address = models.TextField()

    # 3. REQUIRED_FIELDS
    REQUIRED_FIELDS = ['first_name',
                       'last_name',
                       'role',
                       'phone_number',
                       'date_of_birth',
                       'address']

    # 4. ИСПРАВЛЕНИЕ: Добавлен обязательный позиционный аргумент 'to' ('auth.Group')
    groups = models.ManyToManyField(
        'auth.Group',  # <-- ОБЯЗАТЕЛЬНЫЙ АРГУМЕНТ 'to'
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    # 5. ИСПРАВЛЕНИЕ: Добавлен обязательный позиционный аргумент 'to' ('auth.Permission')
    user_permissions = models.ManyToManyField(
        'auth.Permission',  # <-- ОБЯЗАТЕЛЬНЫЙ АРГУМЕНТ 'to'
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    class Meta:
        db_table = 'custom_user'

###############################################################
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
###############################################################

class ClinicOwner(models.Model):
    id = models.AutoField(primary_key=True)
    name_clinic = models.CharField(max_length=200)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE,)

    class Meta:
        db_table = 'clinic_owners'


class Branch(models.Model):
    id = models.AutoField(primary_key=True)
    address = models.TextField()

    # Это поле будем использовать для ПРАЗДНИКОВ (например: "8 Марта")
    description = models.TextField(null=True, blank=True)

    # Новые поля для настроек
    working_hours = models.CharField(max_length=100, default="10:00 - 17:00")
    off_days = models.CharField(max_length=100, default="Сб, Вс")

    clinic_owner = models.ForeignKey(ClinicOwner, on_delete=models.CASCADE)

    class Meta:
        db_table = 'branches'

class Manager(models.Model):
    id = models.AutoField(primary_key=True)

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='managers'  # <-- Важно! Это имя будет использоваться для обратной связи
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    class Meta:
        db_table = 'managers'


class Doctor(models.Model):
    SPECIALIZATION_CHOICES = (
        ('therapist', 'Терапевт'),
        ('surgeon', 'Хирург'),
        ('pediatrician', 'Педиатр'),
        ('cardiologist', 'Кардиолог'),
        ('neurologist', 'Невролог'),
        ('dentist', 'Стоматолог'),
        ('ophthalmologist', 'Офтальмолог'),
        ('dermatologist', 'Дерматолог'),
        ('psychiatrist', 'Психиатр'),
        ('other', 'Другое'),
    )

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    description = models.TextField()
    experience_years = models.PositiveIntegerField()
    education = models.TextField()

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    class Meta:
        db_table = 'doctors'

###############################################################


