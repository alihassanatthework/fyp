"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.static import serve as static_serve
from django.urls import re_path

from pathlib import Path

# React single-server integration:
# If `react/build` exists, Django will serve React (index.html + /static/*) and
# let React Router handle all non-API/non-admin routes.
REACT_BUILD_DIR = Path(settings.BASE_DIR) / "react" / "build"
REACT_STATIC_DIR = REACT_BUILD_DIR / "static"

def react_index(_request):
    index_path = REACT_BUILD_DIR / "index.html"
    if not index_path.exists():
        return HttpResponse(
            "React build not found. Run `npm run build` in the `react/` folder.",
            status=500,
        )
    response = HttpResponse(index_path.read_text(encoding="utf-8"), content_type="text/html")
    # Prevent browsers from caching index.html so they always pick up the
    # latest hashed JS/CSS bundle after a rebuild. (The bundles themselves
    # have content hashes in their names, so they're safe to cache forever.)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response

urlpatterns = [
    path('admin/', admin.site.urls),

    # React frontend API (JSON endpoints). The frontend is React-only —
    # the legacy Django template UI was removed.
    path('api/', include('config.api.urls')),
]

# Serve uploaded images (/media/*) and static assets BEFORE the React catch-all.
# Order matters: the React regex below matches anything not starting with
# `api/` or `admin/`, so without these routes registered first the catch-all
# would swallow /media/* requests and return index.html instead of the image.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Catch-all: send unknown routes to React so react-router can render.
# Note: `api/`, `admin/`, and `/media/*` are matched earlier and won't reach this.
if REACT_BUILD_DIR.exists():
    urlpatterns += [
        re_path(r"^(?!api/|admin/|media/).*$", react_index),
    ]
