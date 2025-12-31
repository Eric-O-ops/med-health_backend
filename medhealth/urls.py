from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Импортируем представления из вашего файла view.py
from .view import (
    RequestListCreateView, RequestDetailView, ManagerViewSet,
    UserViewSet, AdminViewSet, ClinicOwnerViewSet,
    BranchViewSet, DoctorViewSet
)

# 1. Настройка Роутера
router = DefaultRouter()
router.register('users', UserViewSet)
router.register('admins', AdminViewSet)
router.register('owners', ClinicOwnerViewSet)
router.register('branches', BranchViewSet)
router.register('doctors', DoctorViewSet)
router.register('managers', ManagerViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Все ViewSet'ы будут доступны по адресу /api/...
    path('api/', include(router.urls)),

    # Маршруты для Requests
    path('api/requests/', RequestListCreateView.as_view(), name='request-list-create'),
    path('api/requests/<int:pk>/', RequestDetailView.as_view(), name='request-detail'),
]

# 2. ПОДКЛЮЧЕНИЕ МЕДИА ФАЙЛОВ (Чтобы фото не были белыми)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)