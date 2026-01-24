from datetime import datetime
from rest_framework import generics, viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response

# Импорт твоих моделей
from .models import (
    CustomUser, Admin, ClinicOwner, Branch,
    Doctor, Requests, Manager, Appointment
)
from .serializers import (
    CustomUserSerializer, AdminSerializer, ClinicOwnerNestedSerializer,
    BranchSerializer, DoctorSerializer, RequestSerializer, ManagerSerializer,
    AppointmentRegisterSerializer, AppointmentSlotSerializer, AppointmentCancelSerializer,
)

# --- Представления для Requests (Заявки) ---
class RequestListCreateView(generics.ListCreateAPIView):
    queryset = Requests.objects.all()
    serializer_class = RequestSerializer

class RequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Requests.objects.all()
    serializer_class = RequestSerializer

# --- ViewSets для основных сущностей ---
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
    def get_queryset(self):
        queryset = Branch.objects.all()
        if self.action == 'list':
            owner_id = self.request.query_params.get('owner_id')
            if owner_id and owner_id != 'null':
                queryset = queryset.filter(clinic_owner_id=owner_id)
        return queryset

class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer
    def get_queryset(self):
        queryset = Manager.objects.all()
        owner_id = self.request.query_params.get('owner_id')
        if owner_id:
            queryset = queryset.filter(branch__clinic_owner_id=owner_id)
        return queryset

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    def get_queryset(self):
        queryset = Doctor.objects.all()
        branch_id = self.request.query_params.get('branch_id')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset
    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        user.delete()

# --- Эндпоинты для календаря врача ---
class DoctorDailyAppointmentsView(APIView):
    def post(self, request):
        date_str = request.data.get('date')
        doctor_id = request.data.get('doctorId')
        appointments = Appointment.objects.filter(doctor_id=doctor_id, date=date_str)
        data = []
        for app in appointments:
            data.append({
                'id': app.id,
                'patient_id': app.patient.id,
                'doctor_id': app.doctor.id,
                'status': app.status,
                'time': app.time.strftime('%H:%M'),
                'date': app.date.strftime('%Y-%m-%d'),
                'symptomsDescribedByPatient': app.symptomsDescribedByPatient,
                'selfTreatmentMethodsTaken': app.selfTreatmentMethodsTaken,
            })
        return Response(data)

class PatientAttendedView(APIView):
    def post(self, request):
        d_id = request.data.get('doctorId')
        p_id = request.data.get('patientId')
        date = request.data.get('date')
        time_data = request.data.get('time')
        time_obj = datetime.time(hour=time_data['hour'], minute=time_data['minute'])
        try:
            app = Appointment.objects.get(doctor_id=d_id, patient_id=p_id, date=date, time=time_obj)
            app.status = 'completed'
            app.save()
            return Response({'status': 'ok'})
        except Appointment.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)


class AppointmentNoShowView(APIView):
    """
    POST /api/appointments/no-show-by-data/
    Отмечает, что пациент не пришел.
    """

    def post(self, request):
        d_id = request.data.get('doctorId')
        p_id = request.data.get('patientId')
        date = request.data.get('date')
        time_data = request.data.get('time')

        # Превращаем данные времени из Flutter в объект времени Python
        try:
            time_obj = datetime.time(hour=time_data['hour'], minute=time_data['minute'])
            app = Appointment.objects.get(doctor_id=d_id, patient_id=p_id, date=date, time=time_obj)
            app.status = 'no_show'
            app.save()
            return Response({'status': 'ok', 'message': 'Status updated to no_show'})
        except (Appointment.DoesNotExist, TypeError, KeyError):
            return Response({'error': 'Appointment not found or invalid data'}, status=404)

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



# --- НОВЫЙ ЭНДПОИНТ ДЛЯ ПАЦИЕНТА (КЛИНИКИ) ---
class AllClinicsListView(APIView):
    def get(self, request):
        owners = ClinicOwner.objects.all()
        data = []
        for owner in owners:
            data.append({
                'id': owner.id,
                'name_clinic': owner.name_clinic,
                'branches_count': Branch.objects.filter(clinic_owner=owner).count(),
            })
        return Response(data)