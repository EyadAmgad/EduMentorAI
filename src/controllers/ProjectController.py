import os
from django.conf import settings

class ProjectController:
    def get_project_path(self, project_id: str):
        project_path = os.path.join(settings.MEDIA_ROOT, "ass", project_id)
        os.makedirs(project_path, exist_ok=True)
        return project_path
