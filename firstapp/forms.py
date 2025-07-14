from django import forms
from .models import Skill

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'level', 'group', 'subgroup']
        widgets = {
            'level': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: limit choices, e.g. exclude already selected skills
        # if 'user' in kwargs:
        #     user = kwargs['user']
        #     self.fields['name'].queryset = SkillName.objects.exclude(
        #         id__in=user.skill.values_list('name_id', flat=True)
        #     )