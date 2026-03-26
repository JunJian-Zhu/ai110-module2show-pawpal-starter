"""Pytest suite for PawPal+ core logic."""

import sys
import os
from datetime import datetime, timedelta

# Ensure the project root is on the path when running from the tests/ subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pawpal_system import Owner, Pet, Scheduler, Task


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def base_time():
    """Return a fixed datetime to make tests deterministic."""
    return datetime(2025, 6, 15, 9, 0, 0)


@pytest.fixture
def owner_with_pets(base_time):
    """Return an Owner with two pets and several tasks."""
    owner = Owner("Test Owner", "test@test.com")
    buddy = Pet(name="Buddy", species="dog", breed="Labrador", age=3)
    whiskers = Pet(name="Whiskers", species="cat", breed="Siamese", age=5)

    buddy.add_task(Task("Morning walk", base_time,              "daily",  "High",   "Buddy"))
    buddy.add_task(Task("Feeding",      base_time + timedelta(hours=2), "daily",  "Medium", "Buddy"))
    whiskers.add_task(Task("Playtime",  base_time + timedelta(hours=1), "daily",  "Low",    "Whiskers"))
    whiskers.add_task(Task("Vet visit", base_time + timedelta(hours=3), "once",   "High",   "Whiskers"))

    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    return owner, buddy, whiskers


# ── Task tests ────────────────────────────────────────────────────────────────

def test_mark_complete_changes_status(base_time):
    """mark_complete() should flip is_complete to True."""
    task = Task("Walk", base_time, "once", "High", "Buddy")
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_mark_complete_once_returns_none(base_time):
    """Completing a 'once' task should not generate a next occurrence."""
    task = Task("Vet", base_time, "once", "High", "Buddy")
    result = task.mark_complete()
    assert result is None


def test_mark_complete_daily_returns_next_day(base_time):
    """Completing a daily task should return a new task scheduled one day later."""
    task = Task("Feeding", base_time, "daily", "Medium", "Buddy")
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_time == base_time + timedelta(days=1)
    assert next_task.is_complete is False
    assert next_task.description == task.description


def test_mark_complete_weekly_returns_next_week(base_time):
    """Completing a weekly task should return a new task scheduled one week later."""
    task = Task("Grooming", base_time, "weekly", "Low", "Whiskers")
    next_task = task.mark_complete()
    assert next_task is not None
    assert next_task.due_time == base_time + timedelta(weeks=1)


def test_reschedule_updates_due_time(base_time):
    """reschedule() should update the task's due_time."""
    task = Task("Meds", base_time, "once", "High", "Buddy")
    new_time = base_time + timedelta(hours=5)
    task.reschedule(new_time)
    assert task.due_time == new_time


# ── Pet tests ─────────────────────────────────────────────────────────────────

def test_add_task_increases_count(base_time):
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet("Buddy", "dog", "Labrador", 3)
    initial = len(pet.tasks)
    pet.add_task(Task("Walk", base_time, "daily", "High", "Buddy"))
    assert len(pet.tasks) == initial + 1


def test_remove_task_decreases_count(base_time):
    """Removing a task from a Pet should decrease its task list by one."""
    pet = Pet("Buddy", "dog", "Labrador", 3)
    task = Task("Walk", base_time, "daily", "High", "Buddy")
    pet.add_task(task)
    pet.remove_task(task)
    assert task not in pet.tasks


def test_pet_with_no_tasks():
    """A freshly created Pet should have an empty task list."""
    pet = Pet("Mochi", "cat", "Persian", 2)
    assert pet.get_tasks() == []


# ── Owner tests ───────────────────────────────────────────────────────────────

def test_empty_owner_has_no_tasks():
    """A new Owner with no pets should return an empty task list."""
    owner = Owner("Jordan", "jordan@test.com")
    assert owner.get_all_tasks() == []


def test_get_all_tasks_spans_all_pets(owner_with_pets):
    """get_all_tasks() should return tasks from every pet."""
    owner, buddy, whiskers = owner_with_pets
    all_tasks = owner.get_all_tasks()
    assert len(all_tasks) == len(buddy.tasks) + len(whiskers.tasks)


# ── Scheduler tests ───────────────────────────────────────────────────────────

def test_sort_by_time_is_chronological(owner_with_pets):
    """sort_by_time() must return tasks in ascending due_time order."""
    owner, _, _ = owner_with_pets
    scheduler = Scheduler(owner)
    tasks = scheduler.sort_by_time()
    times = [t.due_time for t in tasks]
    assert times == sorted(times)


def test_sort_by_priority_high_first(owner_with_pets):
    """sort_by_priority() must put High-priority tasks before Lower ones."""
    owner, _, _ = owner_with_pets
    scheduler = Scheduler(owner)
    tasks = scheduler.sort_by_priority()
    assert tasks[0].priority == "High"


def test_filter_by_pet_returns_correct_pet(owner_with_pets):
    """filter_by_pet('Buddy') should return only Buddy's tasks."""
    owner, buddy, _ = owner_with_pets
    scheduler = Scheduler(owner)
    result = scheduler.filter_by_pet("Buddy")
    assert all(t.pet_name == "Buddy" for t in result)
    assert len(result) == len(buddy.tasks)


def test_filter_by_status_pending(owner_with_pets):
    """filter_by_status(False) should return only incomplete tasks."""
    owner, _, _ = owner_with_pets
    scheduler = Scheduler(owner)
    pending = scheduler.filter_by_status(is_complete=False)
    assert all(not t.is_complete for t in pending)


def test_filter_by_status_complete(owner_with_pets):
    """filter_by_status(True) should return only completed tasks."""
    owner, buddy, _ = owner_with_pets
    buddy.tasks[0].mark_complete()  # mark one task done
    scheduler = Scheduler(owner)
    done = scheduler.filter_by_status(is_complete=True)
    assert len(done) == 1
    assert done[0].is_complete is True


def test_detect_conflicts_flags_same_time(base_time):
    """detect_conflicts() should flag two tasks for the same pet at the same time."""
    owner = Owner("Jordan", "j@test.com")
    pet = Pet("Rex", "dog", "Poodle", 2)
    pet.add_task(Task("Walk",    base_time, "once", "High",   "Rex"))
    pet.add_task(Task("Bath",    base_time, "once", "Medium", "Rex"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    warnings = scheduler.detect_conflicts()
    assert len(warnings) >= 1
    assert "Rex" in warnings[0]


def test_detect_conflicts_no_false_positives(owner_with_pets):
    """detect_conflicts() should return no warnings when tasks are at different times."""
    owner, _, _ = owner_with_pets
    scheduler = Scheduler(owner)
    # Remove the conflicting-time tasks; fixture already has unique times
    warnings = scheduler.detect_conflicts()
    assert warnings == []


def test_handle_recurring_adds_next_task(base_time):
    """handle_recurring() should add the next occurrence to the pet's task list."""
    owner = Owner("Sam", "sam@test.com")
    pet = Pet("Buddy", "dog", "Lab", 3)
    task = Task("Walk", base_time, "daily", "High", "Buddy")
    pet.add_task(task)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    initial_count = len(pet.tasks)
    scheduler.handle_recurring(task, pet)
    assert len(pet.tasks) == initial_count + 1
    assert pet.tasks[-1].due_time == base_time + timedelta(days=1)


def test_handle_recurring_once_does_not_add(base_time):
    """handle_recurring() on a 'once' task should not add a new task."""
    owner = Owner("Sam", "sam@test.com")
    pet = Pet("Whiskers", "cat", "Siamese", 5)
    task = Task("Vet", base_time, "once", "High", "Whiskers")
    pet.add_task(task)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    scheduler.handle_recurring(task, pet)
    assert len(pet.tasks) == 1  # no new task added


def test_find_next_available_slot_avoids_busy_times(base_time):
    """find_next_available_slot() should skip slots occupied by existing tasks."""
    owner = Owner("Alex", "a@test.com")
    pet = Pet("Buddy", "dog", "Lab", 3)
    # Fill the next several 30-min boundaries from base_time
    busy_times = [base_time + timedelta(minutes=30 * i) for i in range(6)]
    for bt in busy_times:
        pet.add_task(Task("Task", bt, "once", "Low", "Buddy"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    slot = scheduler.find_next_available_slot(pet, duration_minutes=30)
    # Slot must not collide with any existing task
    assert slot is not None
    assert slot not in busy_times


def test_get_daily_schedule_only_today(base_time):
    """get_daily_schedule() should exclude tasks on other dates."""
    owner = Owner("Alex", "a@test.com")
    pet = Pet("Buddy", "dog", "Lab", 3)
    today_task = Task("Walk", base_time,                    "once", "High", "Buddy")
    tmrw_task  = Task("Walk", base_time + timedelta(days=1), "once", "High", "Buddy")
    pet.add_task(today_task)
    pet.add_task(tmrw_task)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    schedule = scheduler.get_daily_schedule(date=base_time)
    assert today_task in schedule
    assert tmrw_task not in schedule
