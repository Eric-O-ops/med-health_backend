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
    AppointmentNoShowView, AllClinicsListView,  # Здесь горит красным AppointmentNoShowView
    AppointmentSlotsView, AppointmentRegisterView, AppointmentCancelView  # Добавлены новые
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

    path('api/patient/clinics/', AllClinicsListView.as_view()),
    path('api/requests/', RequestListCreateView.as_view(), name='request-list-create'),
    path('api/requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),

    # Календарь и записи
    path('api/appointments/slots/current-day', AppointmentSlotsView.as_view()),
    path('api/appointments/register', AppointmentRegisterView.as_view()),
    path('api/doctors/appointments/daily/', DoctorDailyAppointmentsView.as_view()),
    path('api/appointments/patient-attended/', PatientAttendedView.as_view()),
    path('api/appointments/no-show-by-data/', AppointmentNoShowView.as_view()),
    path('api/appointments/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),  # <-- НОВЫЙ МАРШРУТ

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)