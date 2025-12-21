from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from medhealth.models import Requests, Manager, Appointment
from medhealth.serializers import RequestSerializer, ManagerSerializer, BranchBySerializer, \
    ClinicWithBranchesSerializer, AppointmentSlotSerializer, AppointmentRegisterSerializer, AppointmentCancelSerializer, \
    AppointmentNoShowSerializer, AppointmentHistorySerializer, AppointmentCompleteSerializer, \
    AppointmentHistoryRequestSerializer, DoctorDailyAppointmentsRequestSerializer
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser, Admin, ClinicOwner, Branch, Doctor
from .serializers import (
    CustomUserSerializer, AdminSerializer, ClinicOwnerNestedSerializer,
    BranchSerializer, DoctorSerializer
)

from datetime import datetime, timedelta, time

class PatientAttendedView(generics.GenericAPIView):
    """
    POST /api/appointments/patient-attended/
    Аналог complete-by-data. Отмечает запись как 'Завершен' (completed).
    """
    serializer_class = AppointmentCompleteSerializer # Используем тот же сериализатор

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Используем тот же метод, который устанавливает статус 'completed'
            updated_count = serializer.mark_completed()

            if updated_count == 0:
                return Response(
                    {"detail": "Запись не найдена по указанным данным."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"detail": "Пациент успешно отмечен как пришедший.", "status": "completed"},
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
             return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": f"Непредвиденная ошибка: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DoctorDailyAppointmentsView(generics.GenericAPIView):
    """
    POST /api/doctors/appointments/daily/
    Возвращает все записи для конкретного доктора на указанную дату,
    принимая doctorId и date в теле запроса.
    """
    serializer_class = DoctorDailyAppointmentsRequestSerializer  # Сериализатор для входных данных

    def post(self, request, *args, **kwargs):
        # 1. Валидация входных данных
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated_data = input_serializer.validated_data

        doctor_id = validated_data['doctorId']
        date = validated_data['date']

        # 2. Формирование QuerySet: Фильтрация по doctorId и date
        queryset = Appointment.objects.filter(
            doctor_id=doctor_id,
            date=date
        ).order_by('time')  # Сортируем по времени

        # 3. Сериализация результата для вывода
        # Используем AppointmentHistorySerializer, так как он отображает
        # ID, дату, время, doctor_id, status, symptoms и selfTreatment
        output_serializer = AppointmentHistorySerializer(queryset, many=True)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class PatientAppointmentHistoryByDataView(generics.GenericAPIView):
    """
    POST /api/patients/appointments/history/
    Возвращает историю записей (включая статус) для определенного пациента,
    фильтруя по doctorId и date, переданным в теле запроса.
    """
    serializer_class = AppointmentHistoryRequestSerializer  # Сериализатор для входных данных

    def post(self, request, *args, **kwargs):
        # 1. Валидация входных данных
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validated_data = input_serializer.validated_data

        patient_id = validated_data['patientId']
        doctor_id = validated_data.get('doctorId')
        date = validated_data.get('date')

        # 2. Формирование QuerySet
        queryset = Appointment.objects.filter(patient_id=patient_id)

        if doctor_id is not None:
            queryset = queryset.filter(doctor_id=doctor_id)

        if date is not None:
            queryset = queryset.filter(date=date)

        # 3. Сортировка
        queryset = queryset.order_by('-date', '-time')

        # 4. Сериализация результата для вывода
        # Используем существующий AppointmentHistorySerializer для форматирования ответа
        output_serializer = AppointmentHistorySerializer(queryset, many=True)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class AppointmentCompleteByDataView(generics.GenericAPIView):
    """
    POST /api/appointments/complete-by-data/
    Отмечает запись как 'Завершен' (completed) по ID доктора, ID пациента, дате и времени.
    """
    serializer_class = AppointmentCompleteSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_count = serializer.mark_completed()

            if updated_count == 0:
                return Response(
                    {"detail": "Запись не найдена по указанным данным. Проверьте ID доктора, пациента, дату и время."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"detail": "Запись успешно отмечена как 'Завершен'.", "status": "completed"},
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": f"Непредвиденная ошибка при обновлении записи: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PatientAppointmentHistoryView(generics.ListAPIView):
    """
    GET /api/patients/{patient_id}/appointments/history/?doctor_id=X&date=YYYY-MM-DD
    Возвращает записи для определенного пациента, отфильтрованные по доктору и дате.
    """
    serializer_class = AppointmentHistorySerializer

    def get_queryset(self):
        # 1. Получаем ID пациента из URL (Path Parameter)
        patient_id = self.kwargs.get('patient_id')

        # 2. Получаем параметры фильтрации из GET-запроса (Query Parameters)
        doctor_id_param = self.request.query_params.get('doctor_id')
        date_param = self.request.query_params.get('date')

        # Проверка, что пользователь существует
        get_object_or_404(CustomUser, id=patient_id, role='patient')

        # Начинаем фильтрацию с ID пациента
        queryset = Appointment.objects.filter(patient_id=patient_id)

        # 3. Фильтруем по ID доктора, если он предоставлен
        if doctor_id_param:
            try:
                # Проверка существования доктора (опционально)
                Doctor.objects.get(id=doctor_id_param)
                queryset = queryset.filter(doctor_id=doctor_id_param)
            except Doctor.DoesNotExist:
                # Если доктор не найден, возвращаем пустой QuerySet, чтобы не было ошибки 404
                return Appointment.objects.none()

        # 4. Фильтруем по дате, если она предоставлена
        if date_param:
            try:
                # Проверка корректности формата даты
                appointment_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                queryset = queryset.filter(date=appointment_date)
            except ValueError:
                # В случае неверного формата даты, можно вернуть ошибку или пустой QuerySet
                # В данном случае, возвращаем пустой набор, чтобы не прерывать работу
                return Appointment.objects.none()

        # 5. Сортировка результата
        return queryset.order_by('-date', '-time')


class AppointmentCancelView(generics.GenericAPIView):
    """
    POST /api/appointments/cancel/
    Отменяет запись по ID пациента, ID доктора, дате и времени.
    """
    serializer_class = AppointmentCancelSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            deleted_count = serializer.cancel_appointment()

            if deleted_count == 0:
                return Response(
                    {"detail": "Запись не найдена по указанным данным. Проверьте ID доктора, пациента, дату и время."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"detail": "Запись успешно отменена."},
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": f"Непредвиденная ошибка при отмене записи: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PatientViewSet(viewsets.ModelViewSet):
    """
    CRUD операции для сущности Пациент (CustomUser с role='patient').
    """
    # 1. Задаем queryset: Только пользователи с ролью 'patient'
    queryset = CustomUser.objects.filter(role='patient')

    # 2. Используем CustomUserSerializer
    serializer_class = CustomUserSerializer

    # 3. Переопределяем perform_create, чтобы гарантировать роль 'patient'
    def perform_create(self, serializer):
        # Мы уже установили validated_data['role'] = 'patient' в CustomUserSerializer.create,
        # но этот метод полезен для дополнительной логики или проверки.
        serializer.save()

    # 4. Переопределяем get_queryset для возможности GET запроса по id
    # Это гарантирует, что даже при запросе по PK, мы получим только пациента.
    def get_queryset(self):
        return self.queryset


class SlotData:
    def __init__(self, date, time, status, patient_id=None,
                 symptomsDescribedByPatient=None,  # <-- НОВОЕ
                 selfTreatmentMethodsTaken=None):  # <-- НОВОЕ
        self.date = date
        self.time = time
        self.status = status
        self.patient_id = patient_id
        self.symptomsDescribedByPatient = symptomsDescribedByPatient
        self.selfTreatmentMethodsTaken = selfTreatmentMethodsTaken

    def get_date_time_iso(self):
        return datetime.combine(self.date, self.time).isoformat() + 'Z'

class AppointmentSlotsView(generics.GenericAPIView):
    """
    POST /api/appointments/slots/current-day
    Получает список занятых слотов (busy/mine) для указанного доктора на определенную дату.
    """
    serializer_class = AppointmentSlotSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        date_str = data.get('date')
        doctor_id = data.get('doctorId')

        if not date_str or doctor_id is None:
            return Response(
                {"detail": "Обязательные поля 'date' и 'doctorId' не предоставлены."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"detail": "Некорректный формат даты. Используйте YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Получение объекта Doctor (исправление NameError)
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response(
                {"detail": f"Врач с ID={doctor_id} не найден."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Получение занятых слотов
        occupied_appointments = Appointment.objects.filter(
            doctor=doctor,
            date=appointment_date
        )

        # 3. Форматирование результата
        result_slots = []
        current_user_id = request.user.id if request.user.is_authenticated else None

        for appointment in occupied_appointments:
            # ... (логика определения status остается прежней)
            if current_user_id is not None and appointment.patient_id == current_user_id:
                slot_status = 'mine'
            else:
                slot_status = 'busy'

                # Создание SlotData с patient_id и новыми полями
            slot_data = SlotData(
                date=appointment.date,
                time=appointment.time,
                status=slot_status,
                patient_id=appointment.patient_id,
                # ПЕРЕДАЧА ДАННЫХ ИЗ Appointment В SlotData
                symptomsDescribedByPatient=appointment.symptomsDescribedByPatient,
                selfTreatmentMethodsTaken=appointment.selfTreatmentMethodsTaken
            )
            result_slots.append(slot_data)

        # 4. Сериализация и ответ
        serializer = self.get_serializer(result_slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AppointmentNoShowByDataView(generics.GenericAPIView):
    """
    POST /api/appointments/no-show-by-data/
    Отмечает запись как 'Не пришел' (no-show) по ID доктора, ID пациента, дате и времени.
    """
    serializer_class = AppointmentNoShowSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_count = serializer.mark_no_show()

            if updated_count == 0:
                return Response(
                    {"detail": "Запись не найдена по указанным данным. Проверьте ID доктора, пациента, дату и время."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {"detail": "Запись успешно отмечена как 'Не пришел'.", "status": "no_show"},
                status=status.HTTP_200_OK
            )

        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": f"Непредвиденная ошибка при обновлении записи: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AppointmentRegisterView(generics.CreateAPIView):
    """
    POST /api/appointments/register
    Регистрация на прием к доктору на указанную дату и время без аутентификации.
    """
    serializer_class = AppointmentRegisterSerializer

    # Теперь не нужны классы разрешений, требующие аутентификацию
    # permission_classes = [permissions.AllowAny] # Необязательно, если в settings.py REST_FRAMEWORK по умолчанию AllowAny

    # УДАЛЯЕМ get_serializer_context, так как request.user больше не нужен в сериализаторе
    # def get_serializer_context(self):
    #     context = super().get_serializer_context()
    #     context.update({'request': self.request})
    #     return context

    def create(self, request, *args, **kwargs):
        # УДАЛЯЕМ ПРОВЕРКУ АУТЕНТИФИКАЦИИ
        # if not request.user.is_authenticated:
        #     return Response(
        #         {"detail": "Требуется аутентификация."},
        #         status=status.HTTP_401_UNAUTHORIZED
        #     )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)

            return Response(
                {"detail": "Запись успешно создана."},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            # Обработка других возможных ошибок, включая конфликты уникальности
            return Response(
                {"detail": f"Ошибка при создании записи: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RequestListCreateView(generics.ListCreateAPIView):
    """
    Представление для получения списка всех заявок (GET)
    и создания новой заявки (POST).
    """
    queryset = Requests.objects.all()
    serializer_class = RequestSerializer


class RequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения (GET), обновления (PUT/PATCH) и удаления (DELETE)
    одной заявки по её id (pk).
    """
    queryset = Requests.objects.all()
    serializer_class = RequestSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class AdminViewSet(viewsets.ModelViewSet):
    queryset = Admin.objects.all()
    serializer_class = AdminSerializer


class ClinicOwnerViewSet(viewsets.ModelViewSet):
    queryset = ClinicOwner.objects.all()
    serializer_class = ClinicOwnerNestedSerializer


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer


class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class BranchesByOwnerListView(generics.ListAPIView):
    """
    API View для получения списка филиалов, принадлежащих конкретному владельцу клиники.
    Ожидает id основателя клиники в URL.
    """
    serializer_class = BranchBySerializer

    def get_queryset(self):
        # Получаем id владельца клиники из параметров URL (kwargs)
        # Параметр должен называться так же, как и в urls.py (например, 'owner_id')
        owner_id = self.kwargs.get('owner_id')

        if owner_id is not None:
            # Сначала убеждаемся, что ClinicOwner с таким id существует
            try:
                # Используем ClinicOwner.id, так как это primary key
                clinic_owner = ClinicOwner.objects.get(id=owner_id)
            except ClinicOwner.DoesNotExist:
                # Возвращаем пустой QuerySet, если владелец не найден.
                # DRF вернет пустой список [] с кодом 200 OK,
                # но для лучшей обработки ошибок можно переопределить list.
                return Branch.objects.none()

            # Ищем все объекты Branch, связанные с этим ClinicOwner
            # 'clinic_owner' — это имя поля ForeignKey в модели Branch
            queryset = Branch.objects.filter(clinic_owner=clinic_owner)

            # Оптимизация: используем select_related для уменьшения количества запросов к БД (избежание N+1 проблемы)
            queryset = queryset.select_related('clinic_owner')

            return queryset

        # Если id владельца не предоставлен в URL, возвращаем пустой QuerySet или
        # обрабатываем это как ошибку (в данном случае, пустой список)
        return Branch.objects.none()

    # Необязательно: можно переопределить метод list для более явной обработки ошибки "владелец не найден"
    def list(self, request, *args, **kwargs):
        try:
            # Пытаемся получить queryset
            queryset = self.get_queryset()

            # Если queryset пустой, и в URL был owner_id, можно проверить, существует ли владелец
            if not queryset.exists() and self.kwargs.get('owner_id') is not None:
                # Повторная проверка существования ClinicOwner, чтобы определить,
                # была ли это ошибка "владелец не найден" или "филиалы не найдены"
                owner_id = self.kwargs.get('owner_id')
                if not ClinicOwner.objects.filter(id=owner_id).exists():
                    return Response(
                        {"detail": f"Владелец клиники с id={owner_id} не найден."},
                        status=status.HTTP_404_NOT_FOUND
                    )

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# app_name/view.py (Класс FilteredBranchViewSet)

class FilteredClinicOwnerViewSet(viewsets.ReadOnlyModelViewSet):
    # Используем ClinicOwner как основную модель
    queryset = ClinicOwner.objects.all()
    serializer_class = ClinicWithBranchesSerializer

    def get_queryset(self):
        clinic_name_param = self.request.query_params.get('clinic_name')

        # Начинаем с ClinicOwner, так как это модель, которую мы возвращаем
        queryset = ClinicOwner.objects.all()

        # 1. Фильтрация ClinicOwner по названию (ClinicOwner.name_clinic)
        if clinic_name_param:
            clinic_names_list = [n.strip() for n in clinic_name_param.split(',')]

            clinic_q_objects = Q()
            for name in clinic_names_list:
                clinic_q_objects |= Q(name_clinic__icontains=name)  # name_clinic напрямую в ClinicOwner

            queryset = queryset.filter(clinic_q_objects)

        # 2. Фильтрация по специальности (необходима для исключения владельцев, у которых нет подходящих врачей)
        specialization_param = self.request.query_params.get('specialization')

        if specialization_param:
            specializations_list = [s.strip() for s in specialization_param.split(',')]

            # Нам нужно найти ClinicOwner, у которого есть хотя бы один Branch,
            # который связан с Doctor с нужной специальностью.
            specialization_filter = Q()
            for spec in specializations_list:
                # branch__doctor__specialization - путь от ClinicOwner до Doctor
                specialization_filter |= Q(branch__doctor__specialization=spec)

            queryset = queryset.filter(specialization_filter).distinct()

        # Оптимизация: загружаем связанные Branch и Doctor для сериализатора
        # Prefetch('branch_set__doctor_set') или просто Prefetch('branch_set')
        # В данном случае, Prefetch не обязателен, т.к. фильтрация происходит в get_filtered_branches

        return queryset
