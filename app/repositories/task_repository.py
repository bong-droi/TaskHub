from app.models import Project, Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task


class ProjectRepository(BaseRepository[Project]):
    model = Project
