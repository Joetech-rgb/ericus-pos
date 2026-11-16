from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',                              views.login_view,         name='login'),
    path('forgot-password/',                    views.forgot_password,    name='forgot_password'),
    path('logout/',                             views.logout_view,        name='logout'),
    path('setup/',                              views.register_shop,      name='register_shop'),

    # PIN
    path('pin/verify/',                         views.pin_verify,         name='pin_verify'),
    path('pin/change/',                         views.change_pin,         name='change_pin'),

    # Users
    path('users/',                              views.user_list,          name='user_list'),
    path('users/create/',                       views.user_create,        name='user_create'),
    path('users/<int:user_id>/edit/',           views.user_edit,          name='user_edit'),
    path('users/<int:user_id>/toggle/',         views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:user_id>/logout/',         views.force_logout,       name='force_logout'),

    # Profile & Settings
    path('dashboard/',                          views.dashboard,          name='dashboard'),
    path('profile/',                            views.profile,            name='profile'),
    path('shop/',                               views.shop_settings,      name='shop_settings'),
    path('profile/change-password/',            views.change_password,    name='change_password'),
    path('dark-mode/',                          views.toggle_dark_mode,   name='toggle_dark_mode'),

    # AJAX
    path('users/online/',                       views.users_online,       name='users_online'),
]