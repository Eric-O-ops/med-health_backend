from .models import Requests, Manager
from rest_framework import serializers
from .models import (
    CustomUser, Admin, ClinicOwner, Branch, Doctor
)

from .models import Appointment
from rest_framework.exceptions import ValidationError
from datetime import datetime, time

class DoctorDailyAppointmentsRequestSerializer(serializers.Serializer):
    """
    Сериализатор для валидации параметров запроса ежедневных записей врача.
    Принимает doctorId и date.
    """
    doctorId = serializers.IntegerField()
    date = serializers.DateField()

    def validate_doctorId(self, value):
        """Проверяет, что доктор существует."""
        if not Doctor.objects.filter(id=value).exists():
            raise serializers.ValidationError("Доктор с данным ID не найден.")
        return value

class AppointmentHistoryRequestSerializer(serializers.Serializer):
    """
    Сериализатор для валидации параметров поиска истории записей (в теле POST-запроса).
    """
    patientId = serializers.IntegerField()
    # doctorId и date делаем опциональными, чтобы можно было искать всю историю
    doctorId = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.DateField(required=False, allow_null=True)

    def validate_patientId(self, value):
        """Проверяет, что пациент существует."""
        try:
            CustomUser.objects.get(id=value, role='patient')
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Пациент с данным ID не найден.")
        return value

    def validate_doctorId(self, value):
        """Проверяет, что доктор существует, если ID предоставлен."""
        if value is not None:
            if not Doctor.objects.filter(id=value).exists():
                raise serializers.ValidationError("Доктор с данным ID не найден.")
        return value

class AppointmentCompleteSerializer(serializers.Serializer):
    """
    Сериализатор для отметки явки (завершения приема).
    Требует patientId, doctorId, date и time.
    """
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

    def mark_completed(self):
        """Находит запись и обновляет ее статус на 'completed'."""
        validated_data = self.validated_data

        # 1. Извлекаем объект time, который содержит час и минуту
        time_obj = validated_data['time']

        # --- НАЧАЛО ОТЛАДКИ ---
        print("--- DEBUG MARK_COMPLETED ---")
        print(f"Ищем запись для:")
        print(f"  Пациент ID: {validated_data['patientId']}")
        print(f"  Доктор ID: {validated_data['doctorId']}")
        print(f"  Дата: {validated_data['date']}")
        print(f"  Время (Ч:М): {time_obj.hour}:{time_obj.minute}")
        # --- КОНЕЦ ОТЛАДКИ ---

        # 2. Фильтруем по ВСЕМ параметрам, используя __hour и __minute для времени
        appointment_query = Appointment.objects.filter(
            patient_id=validated_data['patientId'],
            doctor_id=validated_data['doctorId'],
            date=validated_data['date'],
            time__hour=time_obj.hour,
            time__minute=time_obj.minute
        )

        # --- НАЧАЛО ОТЛАДКИ ---
        print(f"Найдено записей по заданным параметрам: {appointment_query.count()}")
        print("----------------------------")
        # --- КОНЕЦ ОТЛАДКИ ---

        # 3. Обновляем статус
        updated_count = appointment_query.update(status='completed')

        return updated_count


class AppointmentHistorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения истории записей пациента.
    """
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)

    # НОВОЕ ПОЛЕ: ID пациента
    patient_id = serializers.IntegerField(source='patient.id', read_only=True)  # <-- ДОБАВЛЕНО

    time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Appointment
        fields = (
            'id',
            'date',
            'time',
            'doctor_id',
            'patient_id',  # <-- ДОБАВЛЕНО в Meta.fields
            'status',
            'symptomsDescribedByPatient',
            'selfTreatmentMethodsTaken'
        )


class AppointmentNoShowSerializer(serializers.Serializer):
    """
    Сериализатор для отметки неявки. Требует patientId, doctorId, date и time.
    """
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

    def mark_no_show(self):
        """Находит запись и обновляет ее статус на 'no_show'."""
        validated_data = self.validated_data

        # 1. Проверяем существование пациента и доктора (опционально, но полезно)
        if not CustomUser.objects.filter(id=validated_data['patientId']).exists():
            raise ValidationError({"patientId": "Пациент с данным ID не найден."})
        if not Doctor.objects.filter(id=validated_data['doctorId']).exists():
            raise ValidationError({"doctorId": "Доктор с данным ID не найден."})

        # 2. Фильтруем по всем параметрам, чтобы найти ТОЧНО ОДНУ запись
        appointment_query = Appointment.objects.filter(
            patient_id=validated_data['patientId'],
            doctor_id=validated_data['doctorId'],
            date=validated_data['date'],
            time=validated_data['time']
        )

        # 3. Обновляем статус
        # .update() возвращает количество обновленных записей
        updated_count = appointment_query.update(status='no_show')

        return updated_count

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

class CustomUserSerializer(serializers.ModelSerializer):
    # ... (существующие поля и Meta класс)

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'first_name',
            'last_name',
            'role',  # Поле 'role' должно присутствовать
            'phone_number',
            'date_of_birth',
            'address',
            'password',
            'password_user',
            'email'
        )
        # ... (extra_kwargs)

    # НОВЫЙ МЕТОД: Гарантируем, что роль всегда 'patient' для этого ViewSet
    def validate_role(self, value):
        if value and value != 'patient':
            raise serializers.ValidationError("Роль должна быть установлена как 'patient'.")
        return value

    def create(self, validated_data):
        # Принудительно устанавливаем роль 'patient' при создании
        validated_data['role'] = 'patient'

        # Создание пользователя
        user = CustomUser.objects.create_user(**validated_data)
        return user

# --- Сериализаторы для записи на прием ---

class SlotData:
    """Вспомогательный класс для передачи данных слотов из View в Serializer."""

    def __init__(self, date, time, status, patient_id=None):
        self.date = date
        self.time = time
        self.status = status
        self.patient_id = patient_id  # <-- НОВОЕ ПОЛЕ


# --- Сериализатор для слотов ---

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
    # 'managers' - это managers=Manager.objects.filter(branch=current_branch)
    # Имя поля должно совпадать с related_name в модели Manager
    managers = ManagerSerializer(many=True, read_only=True)

    # Для записи - ID владельца (как и было)
    clinic_owner = ClinicOwnerNestedSerializer(read_only=True)
    clinic_owner_id = serializers.PrimaryKeyRelatedField(
        queryset=ClinicOwner.objects.all(), source='clinic_owner', write_only=True
    )

    class Meta:
        model = Branch
        fields = ('id', 'description', 'address', 'clinic_owner', 'clinic_owner_id', 'managers')


class DoctorSerializer(serializers.ModelSerializer):
    # 1. Вложенный сериализатор для приема данных пользователя
    user = CustomUserSerializer()

    # 2. Поле для Branch (как и прежде)
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', write_only=True
    )

    # Для отображения (GET-запросов) можно использовать ReadOnlyField
    # или отобразить поля пользователя через user=CustomUserSerializer().
    # В данном случае, user уже отобразит все данные.

    class Meta:
        model = Doctor
        fields = (
            'id', 'user', 'specialization', 'description',
            'experience_years', 'education',
            'branch', 'branch_id'
        )
        read_only_fields = ('branch',)

    def create(self, validated_data):
        user_data = validated_data.pop('user')

        # ВАЖНО: Мы НЕ извлекаем 'password_user' отсюда,
        # чтобы он остался в user_data и был передан в .create()

        # Принудительно устанавливаем роль "doctor" для создаваемого пользователя
        user_data['role'] = 'doctor'

        # Создаем CustomUser. Пароль (нехешированный) сохранится в поле
        # password_user, если оно определено в модели CustomUser.
        user = CustomUser.objects.create(**user_data)

        # Здесь нет set_password() и user.save() для хеширования.

        # Создаем Doctor, связывая его с только что созданным CustomUser
        doctor = Doctor.objects.create(user=user, **validated_data)
        return doctor

class BranchBySerializer(serializers.ModelSerializer):

    class Meta:
        model = Branch
        fields = ('id', 'address',)


# app_name/serializers.py
from django.db.models import Prefetch, Q
from .models import ClinicOwner, Branch


class ClinicWithBranchesSerializer(serializers.ModelSerializer):
    filtered_branches = serializers.SerializerMethodField()

    class Meta:
        model = ClinicOwner
        fields = ('id', 'name_clinic', 'filtered_branches')

    def get_filtered_branches(self, clinic_owner):
        request = self.context['request']
        specialization_param = request.query_params.get('specialization')

        # Начинаем с филиалов, связанных с текущим ClinicOwner
        branch_queryset = clinic_owner.branch_set.all()

        # Словарь для хранения найденных специальностей по ID филиала: {branch_id: [spec1, spec2]}
        found_specs_map = {}

        if specialization_param:
            specializations_list = [s.strip() for s in specialization_param.split(',')]

            # --- 1. Фильтрация Branch по специальности (как раньше) ---
            q_objects = Q()
            for spec in specializations_list:
                q_objects |= Q(doctor__specialization=spec)

            branch_queryset = branch_queryset.filter(q_objects).distinct()

            # --- 2. Сбор найденных специальностей ---
            # Для каждого отфильтрованного Branch, находим, какие из запрошенных
            # специальностей присутствуют

            # Предварительно загружаем докторов для оптимизации
            doctors_prefetch = Prefetch('doctor_set', queryset=Doctor.objects.filter(
                specialization__in=specializations_list
            ))

            # Выполняем запрос с Prefetch
            branches_with_doctors = branch_queryset.prefetch_related(doctors_prefetch)

            for branch in branches_with_doctors:
                # Получаем уникальные специальности для текущего Branch
                specs_in_branch = set(d.specialization for d in branch.doctor_set.all())
                found_specs_map[branch.id] = sorted(list(specs_in_branch))

        # Сериализуем отфильтрованный набор филиалов
        # ВАЖНО: Передаем словарь найденных специальностей в контекст дочернего сериализатора
        return FilteredBranchSerializer(
            branch_queryset,
            many=True,
            context={'found_specs_map': found_specs_map}
        ).data

class FilteredBranchSerializer(serializers.ModelSerializer):
    # Новое поле для хранения найденных специальностей
    found_specializations = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ('id', 'address', 'found_specializations')

    def get_found_specializations(self, branch):
        # Этот метод будет заполнен в следующем шаге, когда мы будем вызывать его
        # из родительского сериализатора и передавать контекст.
        # Внутри ClinicWithBranchesSerializer мы передадим список специальностей,
        # которые были найдены в этом branch.
        return self.context.get('found_specs_map', {}).get(branch.id, [])