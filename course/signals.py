import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import ReadingMaterial, CourseMaterial, Course
from django.core.files.storage import default_storage
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SessionCompletion, Course

# ngattt
@receiver(post_save, sender=SessionCompletion)
def generate_certificate_if_course_complete(sender, instance, created, **kwargs):
    course = instance.course
    user = instance.user
    course.check_and_generate_certification(user)
#end of ngattt

@receiver(post_delete, sender=ReadingMaterial)
def auto_delete_reading_material_on_delete(sender, instance, **kwargs):
    # No file to delete, but remove the CourseMaterial entry
    CourseMaterial.objects.filter(material_id=instance.id).delete()

@receiver(post_delete, sender=Course)
def auto_delete_course_image_on_delete(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            default_storage.delete(instance.image.path)

@receiver(pre_save, sender=Course)
def auto_delete_course_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False
    try:
        old_instance = Course.objects.get(pk=instance.pk)
    except Course.DoesNotExist:
        return False

    if old_instance.image and old_instance.image != instance.image:
        if os.path.isfile(old_instance.image.path):
            default_storage.delete(old_instance.image.path)

