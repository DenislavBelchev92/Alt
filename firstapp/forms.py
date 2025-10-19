from django import forms
from .models import Skill, Profile
import yaml
import os
from django.conf import settings

def load_skills_yaml():
    """Load skills data from YAML file"""
    yaml_path = os.path.join(settings.BASE_DIR, 'firstapp', 'skills.yaml')
    try:
        with open(yaml_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return []

def get_skill_choices():
    """Generate choices for skills from YAML file"""
    skills_data = load_skills_yaml()
    choices = []
    
    for group in skills_data:
        group_name = group['group']
        for subgroup in group['subgroups']:
            subgroup_name = subgroup['name']
            for skill in subgroup['skills']:
                # Create a unique identifier for each skill
                skill_key = f"{group_name}|{subgroup_name}|{skill}"
                skill_label = f"{group_name} > {subgroup_name} > {skill}"
                choices.append((skill_key, skill_label))
    
    return choices

class SkillForm(forms.Form):
    skill = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select Skill'
    )
    level = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        label='Skill Level (0-100)'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get all skill choices from YAML
        all_choices = get_skill_choices()
        
        # Filter out skills the user already has
        if user:
            existing_skills = user.skill.all()
            existing_skill_keys = set()
            for skill in existing_skills:
                skill_key = f"{skill.group}|{skill.subgroup}|{skill.name.name}"
                existing_skill_keys.add(skill_key)
            
            # Remove existing skills from choices
            available_choices = [choice for choice in all_choices if choice[0] not in existing_skill_keys]
        else:
            available_choices = all_choices
        
        self.fields['skill'].choices = [('', 'Select a skill...')] + available_choices

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'sur_name', 'last_name', 'age', 'country', 'city', 'profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'id': 'profile-picture-input', 'style': 'display:none;'}),
        }