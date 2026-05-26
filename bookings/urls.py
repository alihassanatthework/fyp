from django.urls import path
from . import views

urlpatterns = [
    path('bookings/',                  views.bookings_list,   name='booking-list'),
    path('bookings/<int:pk>/',         views.booking_detail,  name='booking-detail'),
    path('bookings/<int:pk>/cancel/',  views.cancel_booking,  name='booking-cancel'),
]
