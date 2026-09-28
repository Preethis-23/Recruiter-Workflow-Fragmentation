import os
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from recruiter_workflow_django import views

static_root = str(settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)

urlpatterns = [
    path('', views.index_view, name='index'),
    path('health', views.health_check, name='health_check'),
    path('health/', views.health_check, name='health_check_slash'),
    path('api/', include('recruiter_workflow_django.urls')),

    # Serve static assets from /static/...
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': static_root}),

    # Serve static files at root level (e.g., /style.css, /app.js, fonts, icons)
    re_path(r'^(?P<path>[^/]+\.(?:css|js|png|jpg|jpeg|svg|ico|json|woff|woff2|ttf|eot|map))$', serve, {'document_root': static_root}),
]
