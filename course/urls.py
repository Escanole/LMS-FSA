from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'course'
urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('import-courses/', views.import_course_folder_view, name='import_courses'),
    path('save_last_accessed_material/', views.save_last_accessed_material, name='save_last_accessed_material'),
    path('add/', views.course_add, name='course_add'),
    path('edit/<int:pk>/details/', views.course_edit_detail, name='course_edit_detail'),
    path('edit/<int:pk>/sessions/', views.course_edit_session, name='course_edit_session'),
    path('edit/<int:pk>/topic-tags/', views.course_edit_topic_tags, name='course_edit_topic_tags'),
    path('courses/delete/<int:pk>/', views.course_delete, name='course_delete'),
    path('enroll/<int:pk>/', views.course_enroll, name='course_enroll'),
    path('unenroll/<int:pk>/', views.course_unenroll, name='course_unenroll'),
    path('<int:pk>/detail/', views.course_detail, name='course_detail'),
    path('<int:pk>/enrolled/', views.users_enrolled, name='users_enrolled'),
    path('search/', views.course_search, name='course_search'),
    # Content
    path('<int:pk>/content/<int:session_id>/', views.course_content, name='course_content'),
    path('<int:pk>/content/edit/<int:session_id>/', views.course_content_edit, name='course_content_edit'),
    path('course/<int:pk>/toggle_publish/', views.toggle_publish, name='toggle_publish'),
    path('<int:pk>/toggle-completion/', views.toggle_completion, name='toggle_completion'),
    path('end_viewing_ajax/', views.end_viewing_ajax, name='end_viewing_ajax'),
    # Material
    path('edit/<int:pk>/reorder/<int:session_id>/', views.reorder_course_materials, name='reorder_course_materials'),
    path('reading-material/<int:id>/', views.reading_material_detail, name='reading_material_detail'),
    # Certificate
    path('<int:pk>/generate-certificate/', views.generate_certificate_png, name='generate_certificate'),
    # Topic URLs
    path('topics/', views.topic_tag_list, name='topic_tag_list'),
    path('topics/add/', views.topic_add, name='topic_add'),
    path('topics/edit/<int:pk>/', views.topic_edit, name='topic_edit'),
    path('topics/delete/<int:pk>/', views.topic_delete, name='topic_delete'),

    path('tags/add/', views.tag_add, name='tag_add'),
    path('tags/edit/<int:pk>/', views.tag_edit, name='tag_edit'),
    path('tags/delete/<int:pk>/', views.tag_delete, name='tag_delete'),
    # Discount
    path('apply-discount/', views.apply_discount, name='apply_discount'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)