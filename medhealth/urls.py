from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from .view import (
    RequestListCreateView, RequestDetailView, ManagerViewSet,
    UserViewSet, AdminViewSet, ClinicOwnerViewSet,
    BranchViewSet, DoctorViewSet,
    DoctorDailyAppointmentsView, PatientAttendedView,
    AppointmentNoShowView, AllClinicsListView  # Все импорты здесь
)

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('admins', AdminViewSet)
router.register('owners', ClinicOwnerViewSet)
router.register('branches', BranchViewSet)
router.register('doctors', DoctorViewSet)
router.register('managers', ManagerViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    # Список клиник для пациента
    path('api/patient/clinics/', AllClinicsListView.as_view()),

    # Заявки
    path('api/requests/', RequestListCreateView.as_view(), name='request-list-create'),
    path('api/requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),

    # Календарь врача
    path('api/doctors/appointments/daily/', DoctorDailyAppointmentsView.as_view()),
    path('api/appointments/patient-attended/', PatientAttendedView.as_view()),
    path('api/appointments/no-show-by-data/', AppointmentNoShowView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)