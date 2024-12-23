from django import forms
from .models import InstructorFeedback, CourseFeedback, TrainingProgramFeedback


class InstructorFeedbackForm(forms.ModelForm):
    class Meta:
        model = InstructorFeedback
        fields = ['course_knowledge', 'communication_skills', 'approachability', 'engagement', 'professionalism', 'comments']
        widgets = {
            'course_knowledge': forms.HiddenInput(),
            'communication_skills': forms.HiddenInput(),
            'approachability': forms.HiddenInput(),
            'engagement': forms.HiddenInput(),
            'professionalism': forms.HiddenInput(),
        }

class CourseFeedbackForm(forms.ModelForm):
    class Meta:
        model = CourseFeedback
        fields = [
            'course_material', 'clarity_of_explanation', 'course_structure',
            'practical_applications', 'support_materials',
            'course_comment', 'material_comment'
        ]
        widgets = {
            'course_material': forms.HiddenInput(),
            'clarity_of_explanation': forms.HiddenInput(),
            'course_structure': forms.HiddenInput(),
            'practical_applications': forms.HiddenInput(),
            'support_materials': forms.HiddenInput(),
        }

class TrainingProgramFeedbackForm(forms.ModelForm):
    class Meta:
        model = TrainingProgramFeedback
        fields = ['relevance', 'organization', 'learning_outcomes', 'resources', 'support', 'comments']