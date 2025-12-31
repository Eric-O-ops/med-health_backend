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

    def get_queryset(self):
        # Получаем базовый запрос
        queryset = Branch.objects.all()

        # Если это действие 'list' (получение списка), то фильтруем
        if self.action == 'list':
            owner_id = self.request.query_params.get('owner_id')
            if owner_id and owner_id != 'null':
                queryset = queryset.filter(clinic_owner_id=owner_id)
            # Если owner_id нет, можно вернуть все или пустой список,
            # но для админки лучше вернуть все.

        # Для действий retrieve, update, destroy (удаление/редактирование)
        # мы возвращаем queryset без жесткой фильтрации, чтобы Django нашел ID
        return queryset

class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer

    def get_queryset(self):
        queryset = Manager.objects.all()
        # Фильтруем менеджеров: берем тех, чьи филиалы принадлежат этому владельцу
        owner_id = self.request.query_params.get('owner_id')
        if owner_id:
            queryset = queryset.filter(branch__clinic_owner_id=owner_id)
        return queryset


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def get_queryset(self):
        """
        Добавляем фильтрацию. Если в URL передан branch_id,
        отдаем врачей только этого филиала.
        """
        queryset = Doctor.objects.all()
        branch_id = self.request.query_params.get('branch_id')

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        return queryset

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        user.delete()