# app_name/urls.py

# Импортируем только необходимые модули
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Импортируем представления для модели Requests (должны быть в .views)
from .view import RequestListCreateView, RequestDetailView, ManagerViewSet, BranchesByOwnerListView, \
    FilteredClinicOwnerViewSet, PatientViewSet, AppointmentCancelView, AppointmentNoShowByDataView, \
    AppointmentNoShowByDataView, PatientAppointmentHistoryView, AppointmentCompleteByDataView, \
    PatientAppointmentHistoryByDataView, DoctorDailyAppointmentsView, PatientAttendedView

# Импортируем ViewSet'ы для моделей пользователей/клиники
from .view import (
    UserViewSet,
    AdminViewSet,
    ClinicOwnerViewSet,
    BranchViewSet,
    DoctorViewSet,
    AppointmentSlotsView,
    AppointmentRegisterView,
)

# 1. Создаем роутер и регистрируем все ViewSet
router = DefaultRouter()
router.register('users', UserViewSet)
router.register('admins', AdminViewSet)
router.register('owners', ClinicOwnerViewSet)
router.register('branches', BranchViewSet)
router.register('doctors', DoctorViewSet)
router.register('managers', ManagerViewSet)
router.register(r'branch-filters', FilteredClinicOwnerViewSet, basename='filtered-branches')

# ИСПРАВЛЕНИЕ: Добавьте явное имя 'basename', чтобы избежать конфликта с UserViewSet
router.register('patients', PatientViewSet, basename='patient')  # <--

urlpatterns = [
    # 2. Включаем все сгенерированные роутером URL-адреса
    # Все новые маршруты будут доступны по корневому пути этого приложения (например, /api/users/)
    path('api/', include(router.urls)),

    # 3. Маршруты для модели Requests (если она не использует ViewSet)
    # GET/POST /api/requests/
    path('requests/', RequestListCreateView.as_view(), name='request-list-create'),

    # GET/PUT/PATCH/DELETE /api/requests/{pk}/
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
    path('branches/owner/<int:owner_id>/', BranchesByOwnerListView.as_view(), name='branches-by-owner'),

    # 4. Новые маршруты для записей на прием
    # POST /api/appointments/slots/current-day
    path(
        'api/appointments/slots/current-day',
        AppointmentSlotsView.as_view(),
        name='appointment-slots-current-day'
    ),

    # POST /api/appointments/register
    path(
        'api/appointments/register',
        AppointmentRegisterView.as_view(),
        name='appointment-register'
    ),

    path('api/appointments/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),  # <-- НОВЫЙ МАРШРУТ

    path('api/appointments/no-show-by-data/',
            AppointmentNoShowByDataView.as_view(),
            name='appointment-no-show-by-data'),
    # <-- НОВЫЙ МАРШРУТ
    path('api/patients/appointments/history/',
         PatientAppointmentHistoryByDataView.as_view(),
         name='patient-appointment-history-by-data'),

    # НОВЫЙ МАРШРУТ для отметки 'Пришел' / 'Завершен'
    path('api/doctors/appointments/daily/',
         DoctorDailyAppointmentsView.as_view(),
         name='doctor-daily-appointments'),

path('api/appointments/patient-attended/',
         PatientAttendedView.as_view(),
         name='patient-attended'),
]
