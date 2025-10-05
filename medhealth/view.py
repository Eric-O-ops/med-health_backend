from rest_framework import generics

from medhealth.models import Requests, Manager
from medhealth.serializers import RequestSerializer, ManagerSerializer
from rest_framework import viewsets
from .models import CustomUser, Admin, ClinicOwner, Branch, Doctor
from .serializers import (
    CustomUserSerializer, AdminSerializer, ClinicOwnerNestedSerializer,
    BranchSerializer, DoctorSerializer
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
    # Примечание: Для Doctor и Admin вам может потребоваться специальная
    # логика создания, чтобы создать и CustomUser, и Doctor/Admin за одну операцию.
    # Это делается через переопределение метода perform_create в ViewSet или
    # через более сложную логику в Serializer.


