from .models import Requests, Manager
from rest_framework import serializers
from .models import (
    CustomUser, Admin, ClinicOwner, Branch, Doctor
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
        fields = (
            'id', 'description', 'address', 'clinic_owner',
            'clinic_owner_id', 'managers', 'working_hours', 'off_days'
        )


class DoctorSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), source='branch', write_only=True
    )

    class Meta:
        model = Doctor
        fields = (
            'id', 'user', 'first_name', 'last_name', 'description',
            'experience_years', 'education', 'phone_number',
            'branch', 'branch_id'
        )
        read_only_fields = ('branch',)