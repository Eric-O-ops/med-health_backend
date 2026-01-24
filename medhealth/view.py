import datetime
from rest_framework import generics, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response

# Импорт твоих моделей
from .models import (
    CustomUser, Admin, ClinicOwner, Branch,
    Doctor, Requests, Manager, Appointment
)

# Импорт твоих сериализаторов
from .serializers import (
    CustomUserSerializer, AdminSerializer, ClinicOwnerNestedSerializer,
    BranchSerializer, DoctorSerializer, RequestSerializer, ManagerSerializer
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
    def post(self, request):
        d_id = request.data.get('doctorId')
        p_id = request.data.get('patientId')
        date = request.data.get('date')
        time_data = request.data.get('time')
        time_obj = datetime.time(hour=time_data['hour'], minute=time_data['minute'])
        try:
            app = Appointment.objects.get(doctor_id=d_id, patient_id=p_id, date=date, time=time_obj)
            app.status = 'no_show'
            app.save()
            return Response({'status': 'ok'})
        except Appointment.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

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