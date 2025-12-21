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
    description = models.TextField()
    address = models.TextField()

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

    specialization = models.CharField(
        max_length=50,
        choices=SPECIALIZATION_CHOICES,
        default='other'  # Установите значение по умолчанию
    )

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    class Meta:
        db_table = 'doctors'

class Patient(models.Model):
    # Предполагаем, что CustomUser с ролью 'patient' будет иметь связанную модель Patient
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    class Meta:
        db_table = 'patients'

class Appointment(models.Model):
    id = models.AutoField(primary_key=True)

    # Связь с CustomUser, который является пациентом
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')

    # Связь с моделью Doctor
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE, related_name='appointments')

    # НОВЫЕ ПОЛЯ
    symptomsDescribedByPatient = models.TextField(
        verbose_name='Описанные пациентом симптомы',
        blank=True,  # Разрешаем пустое значение в базе
        default=''
    )
    selfTreatmentMethodsTaken = models.TextField(
        verbose_name='Принятые методы самолечения',
        blank=True,  # Разрешаем пустое значение в базе
        default=''
    )

    APPOINTMENT_STATUS_CHOICES = (
        ('scheduled', 'Запланирован'),
        ('completed', 'Завершен'),
        ('no_show', 'Не пришел'),  # <-- НОВЫЙ СТАТУС
        ('cancelled', 'Отменен'),
    )

    status = models.CharField(
        max_length=20,
        choices=APPOINTMENT_STATUS_CHOICES,
        default='scheduled',
        verbose_name='Статус приема'
    )

    # Дата и время записи
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appointments'
        # Уникальность: один пациент может записаться к одному врачу на одно и то же время/дату только один раз
        unique_together = ('doctor', 'date', 'time')
        # Индекс для ускорения запросов по дате и доктору
        indexes = [
            models.Index(fields=['doctor', 'date']),
        ]
###############################################################


