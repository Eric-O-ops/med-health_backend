# app_name/urls.py

# Импортируем только необходимые модули
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Импортируем представления для модели Requests (должны быть в .views)
from .view import RequestListCreateView, RequestDetailView, ManagerViewSet

# Импортируем ViewSet'ы для моделей пользователей/клиники
from .view import (
    UserViewSet, AdminViewSet, ClinicOwnerViewSet,
    BranchViewSet, DoctorViewSet
)

# 1. Создаем роутер и регистрируем все ViewSet
router = DefaultRouter()
router.register('users', UserViewSet)
router.register('admins', AdminViewSet)
router.register('owners', ClinicOwnerViewSet)
router.register('branches', BranchViewSet)
router.register('doctors', DoctorViewSet)
router.register('managers', ManagerViewSet)

urlpatterns = [
    # 2. Включаем все сгенерированные роутером URL-адреса
    # Все новые маршруты будут доступны по корневому пути этого приложения (например, /api/users/)
    path('api/', include(router.urls)),

    # 3. Маршруты для модели Requests (если она не использует ViewSet)
    # GET/POST /api/requests/
    path('requests/', RequestListCreateView.as_view(), name='request-list-create'),

    # GET/PUT/PATCH/DELETE /api/requests/{pk}/
    path('requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
]

# Убедитесь, что вы удалили: path('api/', include('medhealth.urls')),
# Это должно быть только в главном urls.py проекта!