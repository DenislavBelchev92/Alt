import yaml
from django.core.management.base import BaseCommand
from firstapp.models import SkillGroup, SkillSubgroup, SkillName

class Command(BaseCommand):
    help = 'Load skill groups, subgroups, and skill names from skills.yaml'

    def handle(self, *args, **kwargs):
        with open('firstapp/skills.yaml', 'r') as f:
            data = yaml.safe_load(f)
        for group_data in data:
            group, _ = SkillGroup.objects.get_or_create(name=group_data['group'])
            for subgroup_data in group_data.get('subgroups', []):
                subgroup, _ = SkillSubgroup.objects.get_or_create(group=group, name=subgroup_data['name'])
                for skill_data in subgroup_data.get('skills', []):
                    # Extract the skill name from the skill dictionary
                    skill_name = skill_data['skill']
                    SkillName.objects.get_or_create(subgroup=subgroup, name=skill_name)
        self.stdout.write(self.style.SUCCESS('Skills loaded'))