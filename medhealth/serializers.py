from datetime import time, datetime

from rest_framework.exceptions import ValidationError

from .models import Requests, Manager
from rest_framework import serializers
from .models import (
    CustomUser, Admin, ClinicOwner, Branch, Doctor, Requests, Manager, Appointment
)

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requests
        fields = ('id', 'first_name', 'last_name','name_clinic', 'email', 'phone_number', 'description')

# --- Сериализаторы для связанных моделей (часто используются для вложенности) ---

class CustomUserSerializer(serializers.ModelSerializer):
    # Убираем password при выводе, но разрешаем его задавать
    # Хотя для Auth лучше использовать специальные сериализаторы DRF
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'first_name',
                'last_name',
                       'role',
                       'phone_number',
                       'date_of_birth',
                       'address',
                       'password',
                        'password_user',
                        'email'
        )
        extra_kwargs = {
            'password': {'max_length': 10}
        }


# --- Сериализаторы для основных сущностей ---

class AdminSerializer(serializers.ModelSerializer):
    # Используем UserSerializer для отображения деталей связанного пользователя
    user = CustomUserSerializer()

    class Meta:
        model = Admin
        fields = '__all__'


# Вспомогательный сериализатор для ClinicOwner, чтобы избежать рекурсии в Branch
class ClinicOwnerNestedSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = ClinicOwner
        fields = ('id', 'name_clinic', 'user')

    def create(self, validated_data):
        user_data = validated_data.pop('user')

        password = user_data.pop('password')

        # 1. Извлекаем email, который будем использовать для позиционного аргумента 'username'
        email = user_data['email']

        # 2. Вызываем create_user. user_data ВСЕ ЕЩЕ содержит 'email'.
        # Django увидит email в позиционном аргументе (для USERNAME_FIELD)
        # И email в **user_data (как именованный аргумент), что решает проблему.
        user = CustomUser.objects.create_user(
            email,
            password = password,
            **user_data  # <--- user_data все еще содержит 'email'
        )

        # 3. Создание ClinicOwner
        clinic_owner = ClinicOwner.objects.create(user=user, **validated_data)

        return clinic_owner

class ManagerSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        source='branch',  # <-- DRF использует это имя в validated_data
        write_only=True
    )

    class Meta:
        model = Manager
        # !!! Убедитесь, что 'branch' и 'branch_id' ЕСТЬ в fields
        fields = ('id', 'user', 'branch', 'branch_id')
        read_only_fields = ('branch',)  # <-- Возможно, здесь проблема!

    def create(self, validated_data):
        # 3.1. Извлекаем данные пользователя и филиала
        user_data = validated_data.pop('user')
        branch_instance = validated_data.pop('branch')  # Это объект Branch, благодаря source='branch'

        # 3.2. Создание CustomUser
        password = user_data.pop('password')
        email = user_data['email']

        user = CustomUser.objects.create_user(
            email,  # Позиционный аргумент для USERNAME_FIELD='email'
            password=password,
            **user_data
        )

        # 3.3. Создание Manager, явно передавая созданный user и извлеченный branch
        manager = Manager.objects.create(
            user=user,
            branch=branch_instance,  # <-- Прямая передача объекта Branch
            **validated_data
        )

        return manager

class BranchSerializer(serializers.ModelSerializer):
    managers = ManagerSerializer(many=True, read_only=True)
    clinic_owner = ClinicOwnerNestedSerializer(read_only=True)
    clinic_owner_id = serializers.PrimaryKeyRelatedField(
        queryset=ClinicOwner.objects.all(), source='clinic_owner', write_only=True
    )

    class Meta:
        model = Branch
        fields = (
            'id', 'description', 'address', 'clinic_owner',
            'clinic_owner_id', 'managers', 'working_hours', 'off_days'
        )


import json
from rest_framework import serializers
from .models import CustomUser, Doctor, Branch


class DoctorSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    # Тянем описание (праздники) из филиала
    branch_description = serializers.CharField(source='branch.description', read_only=True)
    education = serializers.CharField(required=False, allow_blank=True, default="Не указано")
    experience_years = serializers.IntegerField(required=False, default=0)
    description = serializers.CharField(required=False, allow_blank=True, default="Описание отсутствует")

    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', write_only=True
    )

    class Meta:
        model = Doctor
        fields = (
            'id', 'user', 'specialization', 'price', 'gender', 'age',
            'photo', 'education', 'experience_years', 'description',
            'working_hours', 'off_days', 'branch', 'branch_id', 'branch_description'
        )
        # Оставляем один четкий список
        read_only_fields = ('branch', 'branch_description')

    def to_internal_value(self, data):
        """
        Метод исправляет проблему Multipart: если 'user' пришел как строка (JSON),
        мы превращаем его обратно в словарь для корректной валидации.
        """
        if isinstance(data.get('user'), str):
            try:
                mutable_data = data.copy()
                mutable_data['user'] = json.loads(data['user'])
                data = mutable_data
            except ValueError:
                pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        branch_instance = validated_data.pop('branch')

        password = user_data.pop('password')
        email = user_data['email']

        # Создаем пользователя с хешированным паролем + сохраняем открытый в password_user
        user = CustomUser.objects.create_user(
            email,
            password=password,
            password_user=password,
            **user_data
        )

        education = validated_data.pop('education', 'Не указано')
        experience_years = validated_data.pop('experience_years', 0)
        description = validated_data.pop('description', 'Описание отсутствует')

        doctor = Doctor.objects.create(
            user=user,
            branch=branch_instance,
            education=education,
            experience_years=experience_years,
            description=description,
            **validated_data
        )
        return doctor

    def update(self, instance, validated_data):
        # Если при обновлении профиля передаются данные юзера
        user_data = validated_data.pop('user', None)
        if user_data:
            user_serializer = CustomUserSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()

        return super().update(instance, validated_data)


class AppointmentSlotSerializer(serializers.Serializer):
    """Сериализатор для отображения слотов приема."""
    # Имя поля busyStatus совпадает с требуемым в ответе
    busyStatus = serializers.CharField(source='status')

    # Используем SerializerMethodField для форматирования datetime
    dateTime = serializers.SerializerMethodField()

    # НОВОЕ ПОЛЕ: ID пациента. Если слот не занят, это будет null.
    patientId = serializers.IntegerField(source='patient_id', allow_null=True)  # <-- ДОБАВЛЕНО
    symptomsDescribedByPatient = serializers.CharField(
        allow_blank=True,
        required=False
    )
    selfTreatmentMethodsTaken = serializers.CharField(
        allow_blank=True,
        required=False
    )

    def get_dateTime(self, obj):
        """Форматирует дату и время в строку ISO 8601 с 'Z'."""
        combined_dt = datetime.combine(obj.date, obj.time)
        return combined_dt.isoformat() + 'Z'


class AppointmentCancelSerializer(serializers.Serializer):
    """Сериализатор для отмены записи. Требует patientId, doctorId, date и time."""

    # Используем IntegerField для ID, так как нам нужно только значение
    patientId = serializers.IntegerField()
    doctorId = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.DictField(child=serializers.IntegerField(min_value=0))

    def validate_time(self, value):
        """Проверяет и конвертирует dict {'hour': h, 'minute': m} в объект time."""
        try:
            hour = value['hour']
            minute = value['minute']
        except KeyError:
            raise ValidationError("Поля 'hour' и 'minute' обязательны в объекте 'time'.")

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Некорректное значение для часа (0-23) или минуты (0-59).")

        return time(hour, minute)

    def cancel_appointment(self):
        """Находит и удаляет запись."""
        validated_data = self.validated_data

        # Проверяем существование пациента и доктора для чистоты кода
        if not CustomUser.objects.filter(id=validated_data['patientId']).exists():
            raise ValidationError({"patientId": "Пациент с данным ID не найден."})
        if not Doctor.objects.filter(id=validated_data['doctorId']).exists():
            raise ValidationError({"doctorId": "Доктор с данным ID не найден."})

        # Фильтруем по всем параметрам, чтобы найти ТОЧНО ОДНУ запись
        deleted_count, _ = Appointment.objects.filter(
            patient_id=validated_data['patientId'],
            doctor_id=validated_data['doctorId'],
            date=validated_data['date'],
            time=validated_data['time']
        ).delete()

        return deleted_count

class AppointmentRegisterSerializer(serializers.Serializer):
    """
    Сериализатор для POST-запроса регистрации на прием, принимает patientId.
    """
    doctorId = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), source='doctor'
    )
    # НОВОЕ ПОЛЕ: patientId, автоматически проверяет, что это CustomUser с ролью 'patient'
    patientId = serializers.PrimaryKeyRelatedField(
        # Важно: фильтруем только пользователей с ролью 'patient'
        queryset=CustomUser.objects.filter(role='patient'),
        source='patient'
    )
    date = serializers.DateField()
    time = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )

    # НОВЫЕ ПОЛЯ
    symptomsDescribedByPatient = serializers.CharField(
        max_length=500,  # Укажите подходящий max_length
        required=False,  # Оставляем их необязательными, как в модели
        allow_blank=True
    )
    selfTreatmentMethodsTaken = serializers.CharField(
        max_length=500,  # Укажите подходящий max_length
        required=False,
        allow_blank=True
    )

    def validate_time(self, value):
        """Проверяет, что поля 'hour' и 'minute' присутствуют и корректны."""
        try:
            hour = value['hour']
            minute = value['minute']
        except KeyError:
            raise ValidationError("Поля 'hour' и 'minute' обязательны в объекте 'time'.")

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValidationError("Некорректное значение для часа (0-23) или минуты (0-59).")

        return time(hour, minute)

    def validate(self, data):
        """Проверяет, что запись на это время уже не существует."""
        doctor = data['doctor']
        date = data['date']
        time_obj = data['time']  # Объект time

        # patient = data['patient'] - объект CustomUser уже присутствует в данных

        # Проверка, существует ли уже запись
        if Appointment.objects.filter(
                doctor=doctor, date=date, time=time_obj
        ).exists():
            raise ValidationError(
                f"Время {time_obj.strftime('%H:%M')} на {date.strftime('%Y-%m-%d')} у этого доктора уже занято."
            )

        # Удалена проверка request.user.is_authenticated и request.user.role

        return data

    def create(self, validated_data):
        # Извлекаем данные, включая новые поля
        doctor = validated_data['doctor']
        date = validated_data['date']
        time_obj = validated_data['time']
        patient = validated_data['patient']

        # Получаем новые поля, используя .pop() для удаления из validated_data
        symptoms = validated_data.pop('symptomsDescribedByPatient', '')
        self_treatment = validated_data.pop('selfTreatmentMethodsTaken', '')

        # Создаем запись, передавая новые поля
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date,
            time=time_obj,
            symptomsDescribedByPatient=symptoms,  # <-- СОХРАНЯЕМ
            selfTreatmentMethodsTaken=self_treatment  # <-- СОХРАНЯЕМ
        )

        return appointment