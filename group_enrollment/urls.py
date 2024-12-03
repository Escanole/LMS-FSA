# enrollment/urls.py
from django.urls import path
from . import views

app_name = 'group_enrollment'

urlpatterns = [
    path('admin/enrollments/', views.enrollment_list_admin, name='admin_enrollment_list'),
    path('admin/enroll/', views.admin_enroll_users, name='admin_enroll_users'),
    path('enroll/', views.enroll_student, name='enroll_student'),
    path('my-courses/', views.enrollment_list, name='enrollment_list'),
    path('edit/<int:enrollment_id>/', views.edit_enrollment, name='edit_enrollment'),  # Edit enrollment
    path('delete/<int:enrollment_id>/', views.delete_enrollment, name='delete_enrollment'),  # Delete enrollment
    path('admin/path-enroll/', views.admin_enroll_users_learning_path, name='admin_enroll_users_learning_path'),
]
