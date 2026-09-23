from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from recruiter_workflow_django import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('health', views.health_check, name='health_check'),
    path('health/', views.health_check, name='health_check_slash'),
    path('api/', include('recruiter_workflow_django.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
