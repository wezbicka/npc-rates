from django.urls import path

from . import views

app_name = 'rates'

urlpatterns = [
    path('', views.OperationView.as_view(), name='rates'),
    path('select_date/', views.DateSelectView.as_view(), name='select_date'),
    path('import_rates/', views.RateView.as_view(), name='import_rates'),
    path('load_rate/', views.RateSelectView.as_view(), name='load_rate'),
    path('get_rate/<str:date_rate>/<str:currency>/', views.RateView.as_view(), name='get_rate'),
]