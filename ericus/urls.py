from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home redirect to dashboard
    path('', lambda request: redirect('login'), name='home'),

    # Core
    path('', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('inventory/', include('inventory.urls')),
    path('purchases/', include('purchases.urls')),
    path('sales/', include('sales.urls')),
    path('customers/', include('customers.urls')),

    # Wholesale
    path('wholesale/', include('wholesale.urls')),

    # Supporting
    path('discounts/', include('discounts.urls')),
    path('expenses/', include('expenses.urls')),
    path('returns/', include('returns.urls')),
    path('audit/', include('audit.urls')),
    path('reports/', include('reports.urls')),
]

from django.urls import re_path
from django.views.static import serve

# Product photos must be served even with DEBUG off (offline/LAN POS).
# Static files (CSS/JS) are served by WhiteNoise after collectstatic.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]