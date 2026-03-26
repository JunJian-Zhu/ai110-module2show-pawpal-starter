# PawPal+ 🐾

**Smart Pet Care Management System** — a Python + Streamlit app that helps busy pet owners schedule, prioritize, and track care tasks for multiple pets using intelligent scheduling algorithms.

---

## Overview

PawPal+ lets you manage care tasks (walks, feedings, vet visits, grooming, medications) across multiple pets. It automatically sorts tasks by time or priority, detects scheduling conflicts, handles recurring tasks, and finds the next open time slot in your schedule — all backed by JSON persistence.

---

## Features

| Feature | Description |
|---|---|
| **Sorting by time** | Tasks sorted chronologically using `sorted()` with a `lambda` key |
| **Sorting by priority** | High → Medium → Low, then by time — uses weighted tuple sort |
| **Filtering by pet** | Returns only tasks assigned to a specified pet |
| **Filtering by status** | Returns pending or completed tasks |
| **Conflict detection** | Warns when two tasks for the same pet share a due time |
| **Recurring tasks** | Daily/weekly tasks auto-generate their next occurrence on completion |
| **Next available slot** | Finds the first open 30-min window in a pet's schedule |
| **Weighted prioritization** | Urgency score = priority weight × (86400 / seconds until due) |
| **Data persistence** | Owner, pets, and tasks serialized to/from `data.json` via JSON |

---

## System Architecture

The project is organized into four classes, visualized in [`uml_diagram.mmd`](uml_diagram.mmd):

```
Owner ──owns──► Pet ──has──► Task
  ▲
  │ manages
Scheduler
```

- **`Task`** (dataclass) — a single care action with description, due time, frequency, priority, and completion state
- **`Pet`** (dataclass) — a pet with personal info and a list of tasks
- **`Owner`** — aggregates pets; handles JSON save/load
- **`Scheduler`** — all scheduling algorithms, operates over the owner's full task set

All classes live in [`pawpal_system.py`](pawpal_system.py).

---

## Smarter Scheduling

### Sort by Time
```python
sorted(tasks, key=lambda t: t.due_time)
```

### Sort by Priority
```python
sorted(tasks, key=lambda t: (-PRIORITY_MAP[t.priority], t.due_time))
```
`PRIORITY_MAP = {"High": 3, "Medium": 2, "Low": 1}` — negated so High sorts first.

### Conflict Detection
Builds a `(pet_name, due_time)` key; a second task at the same key triggers a warning string (never raises an exception).

### Recurring Tasks
`mark_complete()` checks `frequency` and returns a new `Task` with `due_time + timedelta(days=1)` or `+ timedelta(weeks=1)`. The Scheduler's `handle_recurring()` adds this task directly to the pet.

### Next Available Slot
Starts from the next 30-minute boundary, then walks forward in 30-minute increments up to 24 hours, returning the first window with no existing incomplete tasks.

### Weighted Priority Score
```python
priority_weight * (86400 / seconds_until_due)
```
Tasks that are both high-priority and due soon get the highest scores.

---

## Testing PawPal+

```bash
python -m pytest
```

The test suite in [`tests/test_pawpal.py`](tests/test_pawpal.py) covers:

- Task completion changes `is_complete` flag
- Daily/weekly recurrence creates next occurrence
- `once` tasks do not recur
- Adding/removing tasks updates pet task count
- `sort_by_time()` returns tasks in chronological order
- `sort_by_priority()` puts High-priority first
- `filter_by_pet()` returns only the specified pet's tasks
- `filter_by_status()` separates pending from completed
- `detect_conflicts()` flags duplicate (pet, time) pairs
- `handle_recurring()` appends the next task to the pet
- `find_next_available_slot()` skips busy windows
- `get_daily_schedule()` excludes tasks on other dates
- Edge cases: empty owner, pet with no tasks

**Confidence: ⭐⭐⭐⭐⭐** — all algorithmic paths and edge cases covered by 18 tests.

---

## Demo

### CLI Demo
```bash
python main.py
```
Runs a full demo: creates an owner with Buddy (dog) and Whiskers (cat), adds 8 tasks, then demonstrates every feature with color-coded, emoji-annotated tabulate tables.

### Streamlit App
```bash
streamlit run app.py
```
Opens the interactive UI at `http://localhost:8501` with sidebar navigation for Owner Setup, Add Pet, Add Task, View Schedule, and Manage Tasks.

---

## Setup

```bash
# 1. Clone / navigate to project
cd ai110-module2show-pawpal-starter

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install streamlit tabulate pytest

# 4. Run the CLI demo
python main.py

# 5. Launch the Streamlit app
streamlit run app.py

# 6. Run tests
python -m pytest
```

---

## Project Structure

```
├── pawpal_system.py      # Core logic: Owner, Pet, Task, Scheduler
├── main.py               # CLI demo with tabulate tables
├── app.py                # Streamlit UI
├── tests/
│   └── test_pawpal.py    # Pytest suite (18 tests)
├── data.json             # Persistence file (auto-created by main.py or app)
├── uml_diagram.mmd       # Mermaid.js UML class diagram
├── reflection.md         # Design and AI collaboration reflection
└── requirements.txt      # Dependencies
```
