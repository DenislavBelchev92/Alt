from django import forms
from .models import Skill

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'rate']
        widgets = {
            'rate': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }