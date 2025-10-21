import yaml
import os
from django.conf import settings

def skills_context(request):
    """Context processor to make skills data available to all templates"""
    yaml_path = os.path.join(settings.BASE_DIR, 'firstapp', 'skills.yaml')
    try:
        with open(yaml_path, 'r') as file:
            skills_data = yaml.safe_load(file)
            return {'skills_data': skills_data}
    except FileNotFoundError:
        return {'skills_data': []}