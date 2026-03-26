"""PawPal+ core logic: Owner, Pet, Task dataclasses and Scheduler."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

PRIORITY_MAP = {"High": 3, "Medium": 2, "Low": 1}


@dataclass
class Task:
    """Represents a single care task for a pet."""

    description: str
    due_time: datetime
    frequency: str        # "once" | "daily" | "weekly"
    priority: str         # "Low" | "Medium" | "High"
    pet_name: str
    is_complete: bool = False

    def mark_complete(self) -> Optional[Task]:
        """Mark this task done and return the next occurrence for recurring tasks."""
        self.is_complete = True
        if self.frequency == "daily":
            return Task(
                description=self.description,
                due_time=self.due_time + timedelta(days=1),
                frequency=self.frequency,
                priority=self.priority,
                pet_name=self.pet_name,
            )
        if self.frequency == "weekly":
            return Task(
                description=self.description,
                due_time=self.due_time + timedelta(weeks=1),
                frequency=self.frequency,
                priority=self.priority,
                pet_name=self.pet_name,
            )
        return None

    def reschedule(self, new_time: datetime) -> None:
        """Reschedule this task to a new due time."""
        self.due_time = new_time


@dataclass
class Pet:
    """Represents a pet with its personal info and associated tasks."""

    name: str
    species: str
    breed: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's task list if it exists."""
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self) -> List[Task]:
        """Return all tasks for this pet."""
        return list(self.tasks)


class Owner:
    """Represents the pet owner with full JSON persistence support."""

    def __init__(self, name: str, contact_info: str) -> None:
        """Initialize an Owner with a name, contact info, and empty pet list."""
        self.name = name
        self.contact_info = contact_info
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's household."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's household if it exists."""
        if pet in self.pets:
            self.pets.remove(pet)

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all pets owned by this owner."""
        all_tasks: List[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def save_to_json(self, filepath: str = "data.json") -> None:
        """Serialize the owner, pets, and tasks to a JSON file."""
        data = {
            "name": self.name,
            "contact_info": self.contact_info,
            "pets": [],
        }
        for pet in self.pets:
            pet_data = {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age,
                "tasks": [],
            }
            for task in pet.tasks:
                pet_data["tasks"].append(
                    {
                        "description": task.description,
                        "due_time": task.due_time.isoformat(),
                        "frequency": task.frequency,
                        "priority": task.priority,
                        "pet_name": task.pet_name,
                        "is_complete": task.is_complete,
                    }
                )
            data["pets"].append(pet_data)
        with open(filepath, "w") as fh:
            json.dump(data, fh, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str = "data.json") -> Owner:
        """Deserialize an Owner object from a JSON file."""
        with open(filepath, "r") as fh:
            data = json.load(fh)
        if not data.get("name"):
            return cls("", "")
        owner = cls(name=data["name"], contact_info=data["contact_info"])
        for pet_data in data.get("pets", []):
            pet = Pet(
                name=pet_data["name"],
                species=pet_data["species"],
                breed=pet_data["breed"],
                age=pet_data["age"],
            )
            for td in pet_data.get("tasks", []):
                task = Task(
                    description=td["description"],
                    due_time=datetime.fromisoformat(td["due_time"]),
                    frequency=td["frequency"],
                    priority=td["priority"],
                    pet_name=td["pet_name"],
                    is_complete=td["is_complete"],
                )
                pet.tasks.append(task)
            owner.pets.append(pet)
        return owner


class Scheduler:
    """Scheduling engine that operates over an Owner's full task set."""

    def __init__(self, owner: Owner) -> None:
        """Initialize the scheduler with a reference to an Owner."""
        self.owner = owner

    def sort_by_time(self) -> List[Task]:
        """Return all tasks sorted chronologically by due_time."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.due_time)

    def sort_by_priority(self) -> List[Task]:
        """Return all tasks sorted High→Low priority, then by time."""
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda t: (-PRIORITY_MAP.get(t.priority, 1), t.due_time),
        )

    def filter_by_status(self, is_complete: bool) -> List[Task]:
        """Return tasks filtered by completion status."""
        return [t for t in self.owner.get_all_tasks() if t.is_complete == is_complete]

    def filter_by_pet(self, pet_name: str) -> List[Task]:
        """Return tasks belonging to the specified pet name."""
        return [t for t in self.owner.get_all_tasks() if t.pet_name == pet_name]

    def detect_conflicts(self) -> List[str]:
        """Detect tasks scheduled at identical times for the same pet; return warning strings."""
        warnings: List[str] = []
        seen: dict = {}
        for task in self.owner.get_all_tasks():
            key = (task.pet_name, task.due_time)
            if key in seen:
                warnings.append(
                    f"⚠️  Conflict for {task.pet_name}: "
                    f"'{task.description}' and '{seen[key].description}' "
                    f"both at {task.due_time.strftime('%H:%M on %b %d')}"
                )
            else:
                seen[key] = task
        return warnings

    def handle_recurring(self, task: Task, pet: Pet) -> Optional[Task]:
        """Mark a task complete and add its next recurrence to the pet; return the new task."""
        next_task = task.mark_complete()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def find_next_available_slot(
        self, pet: Pet, duration_minutes: int = 30
    ) -> Optional[datetime]:
        """Find the next open time slot for a pet given a desired task duration in minutes."""
        now = datetime.now().replace(second=0, microsecond=0)
        # Round up to the next 30-minute boundary
        bump = 30 - (now.minute % 30) if now.minute % 30 != 0 else 30
        candidate = now + timedelta(minutes=bump)
        pet_times = {t.due_time for t in pet.tasks if not t.is_complete}
        for _ in range(48):  # search up to 24 hours
            window_end = candidate + timedelta(minutes=duration_minutes)
            conflict = any(candidate <= t < window_end for t in pet_times)
            if not conflict:
                return candidate
            candidate += timedelta(minutes=30)
        return None

    def get_daily_schedule(self, date: Optional[datetime] = None) -> List[Task]:
        """Return tasks for a given date sorted by priority then time."""
        if date is None:
            date = datetime.now()
        day_tasks = [
            t
            for t in self.owner.get_all_tasks()
            if t.due_time.date() == date.date()
        ]
        return sorted(
            day_tasks,
            key=lambda t: (-PRIORITY_MAP.get(t.priority, 1), t.due_time),
        )

    def weighted_priority_score(self, task: Task) -> float:
        """Compute a weighted urgency score: higher priority + sooner due = higher score."""
        now = datetime.now()
        priority_weight = PRIORITY_MAP.get(task.priority, 1)
        seconds_until_due = max((task.due_time - now).total_seconds(), 1)
        return priority_weight * (86400 / seconds_until_due)
