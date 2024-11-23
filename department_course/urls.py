from django.urls import path
from . import views

app_name = 'department_course'

urlpatterns = [
    path('', views.department_course_list, name='department_courses'),
    path('add-course/', views.add_course_to_department, name='add_course_to_department'),
    path('remove-course/', views.remove_course_from_department, name='remove_course_from_department'),
    path('get-assessments/<int:course_id>/', views.get_assessments_for_course, name='get_assessments_for_course'),
]
