from django.db import models
from django.conf import settings
from subject.models import Subject

class CollaborationGroup(models.Model):
    group_name = models.CharField(max_length=255)
    course = models.ForeignKey(Subject, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  


    def __str__(self):
        return self.group_name
    
class GroupMember(models.Model):
    group = models.ForeignKey(CollaborationGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        
    def __str__(self):
        return f'{self.user.username} - {self.group.group_name}'
