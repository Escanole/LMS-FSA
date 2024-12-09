from django.urls import path
from . import views

app_name = 'reports'
urlpatterns = [
    # URL to load the report dashboard
    path('dashboard/', views.report_dashboard, name='report_dashboard'),

    path('course-overview/', views.course_overview_report, name='course_overview_report'),
    path('student-enrollment/', views.student_enrollment_report, name='student_enrollment_report'),
    path('course-completion/', views.course_completion_report, name='course_completion_report'),
    path('session-overview/', views.session_overview_report, name='session_overview_report'),
    path('material-usage/', views.material_usage_report, name='material_usage_report'),
    path('enrollment-trends/', views.enrollment_trends_report, name='enrollment_trends_report'),
    path('material-type-distribution/', views.material_type_distribution_report,
         name='material_type_distribution_report'),
    path('tag-report/', views.tag_report, name='tag_report'),
    path('user-progress/', views.user_progress_report, name='user_progress_report'),
    path('instructor-performance/', views.instructor_performance_report, name='instructor_performance_report'),
    path('course-duration/', views.course_duration_report, name='course_duration_report'),
    path('price-report/', views.price_report, name='price_report'),
    path('department-report/', views.department_report, name='department_report'),
    path('course-users-report/', views.course_users_report, name='course_users_report'),
    path('material-duration-report/', views.material_duration_report, name='material_duration_report'),

    path('user/user_overview_report/', views.user_overview_report, name='user_overview_report'),
    path('user/student-id-report/', views.student_id_report, name='student_id_report'),
    path('students/<str:cohort>/', views.get_students_by_cohort, name='get_students_by_cohort'),

    path('user/role-report/', views.role_report, name='role_report'),
    path('user/user_statistics_report/', views.user_statistics_report, name='user_statistics_report'),
    path('user/login-frequency-report/', views.login_frequency_report, name='login_frequency_report'),
    path('user/user_duration_login/', views.user_duration_login, name='user_duration_login'),

]
