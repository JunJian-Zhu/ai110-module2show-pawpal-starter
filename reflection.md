# PawPal+ Project Reflection

---

## 1. System Design

### 1a. Initial Design

My initial design centered on four classes with clear, non-overlapping responsibilities:

- **`Task`** — a pure data object representing one care action. It knows its own description, due time, recurrence frequency, priority, and completion state. It is intentionally kept narrow: its only behaviors are `mark_complete()` and `reschedule()`. This makes it easy to test in isolation and serialize cleanly to JSON.

- **`Pet`** — aggregates tasks and holds identifying information (name, species, breed, age). It provides `add_task()` and `remove_task()` for mutating its task list, and `get_tasks()` for reading it. Keeping the pet as the "owner" of tasks (rather than storing them in a flat global list) means filtering and conflict detection naturally have a pet scope.

- **`Owner`** — aggregates pets and serves as the persistence boundary. `save_to_json()` and `load_from_json()` live here because the owner is the root of the object graph. Any serialization starts from the owner and walks down.

- **`Scheduler`** — all scheduling intelligence lives here, completely separate from the data classes. It holds a reference to an `Owner` and exposes every algorithmic feature as its own method. This separation means data classes remain simple dataclasses and all complex logic is testable through the scheduler's public interface.

I used Python `@dataclass` for `Task` and `Pet` to eliminate boilerplate and get free `__repr__` for debugging. `Owner` and `Scheduler` are plain classes because they have more complex initialization requirements.

### 1b. Design Changes

Several design decisions evolved after AI-assisted review:

1. **`priority` added to `Task` early.** My first sketch had only `description`, `due_time`, and `frequency`. After prompting an AI to review the design for scheduling use cases, it suggested that without a priority field, sorting would have no tiebreaker and conflict resolution would be arbitrary. I added `priority: str` with a `PRIORITY_MAP` dict (`{"High": 3, "Medium": 2, "Low": 1}`) as a translation layer between the human-readable string and the numeric sort key.

2. **`pet_name` denormalized onto `Task`.** Initially tasks didn't store which pet they belonged to — you'd infer that from the `Pet` object containing them. But for filtering, display, and conflict detection, it was much simpler to let each task carry `pet_name` directly. This is a deliberate denormalization: a small redundancy that eliminates every "find which pet owns this task" traversal.

3. **`Scheduler` decoupled from `Pet`.** An earlier version had scheduling methods directly on `Owner`. Moving them to a dedicated `Scheduler` class made the design much cleaner — `Owner` handles data and persistence, `Scheduler` handles algorithms. This also made unit testing much easier, since I could create isolated `Scheduler` instances with small fixture owners.

4. **`handle_recurring` takes a `Pet` parameter.** The initial version looked up the pet internally by `task.pet_name`. After an AI suggestion, I changed it to accept the `Pet` explicitly — this makes the call site more transparent and eliminates a hidden search inside the method.

---

## 2. Scheduling Logic and Tradeoffs

### 2a. Algorithmic Features

**Sort by time** (`sort_by_time`): Uses `sorted()` with `key=lambda t: t.due_time`. Python's `sorted()` is stable and O(n log n). This is the simplest and most useful view for daily planning.

**Sort by priority** (`sort_by_priority`): Uses a two-element tuple key: `(-PRIORITY_MAP[t.priority], t.due_time)`. Negating the priority integer makes `sorted()` order High before Low without needing `reverse=True` on the entire sort (which would also reverse the time ordering).

**Filter by pet** (`filter_by_pet`): A list comprehension over all tasks checking `task.pet_name == pet_name`. O(n) and straightforward.

**Filter by status** (`filter_by_status`): Same pattern, checking `task.is_complete`.

**Conflict detection** (`detect_conflicts`): Builds a dictionary keyed on `(pet_name, due_time)`. On first occurrence of a key the task is stored; on second occurrence a warning string is appended to the output list. The method always returns a list — it never raises exceptions — making it safe to call at any time.

**Recurring tasks** (`mark_complete` + `handle_recurring`): `mark_complete()` checks `frequency` and returns a new `Task` with `due_time + timedelta(days=1)` or `timedelta(weeks=1)`. `handle_recurring()` calls `mark_complete()` and, if a next task is returned, appends it to the pet's task list. The original task's `is_complete` flag is set to `True` in place.

**Next available slot** (`find_next_available_slot`): Starts at the next 30-minute boundary from now, then walks forward in 30-minute increments, checking each candidate window `[candidate, candidate + duration)` against the set of existing incomplete task times. Returns the first conflict-free slot, or `None` if none found within 24 hours.

**Weighted priority score** (`weighted_priority_score`): Computes `priority_weight × (86400 / seconds_until_due)`. A High-priority task due in 1 hour scores `3 × (86400 / 3600) = 72`. The same task due in 24 hours scores `3 × 1 = 3`. This gives an urgency-adjusted ordering that naturally deprioritizes distant high-priority tasks relative to imminent lower-priority ones.

### 2b. Tradeoffs

**Conflict detection is exact-time only.** The current implementation flags two tasks at the *exact same* due time. It does not detect overlapping *durations* — a 30-minute walk starting at 9:00 and a 20-minute feeding starting at 9:15 would not be flagged. This limitation was a deliberate simplicity choice: tasks don't have a duration field in this design (only a due time), so overlap detection would require a separate `duration_minutes` attribute and more complex interval arithmetic. For a pet care app, tasks are typically short and users set times intentionally, so exact-match conflict detection catches the most common mistake (accidentally double-booking a time slot) without adding complexity.

**Next available slot only searches 24 hours.** The finder caps its search at 48 × 30-minute increments (24 hours). If a pet's schedule is completely booked for 24 hours, the method returns `None`. This is a reasonable bound for a daily scheduling tool — if there's no opening in the next 24 hours, the user should restructure the schedule rather than have the app silently schedule days in advance.

**JSON persistence is flat, not relational.** All data is serialized into one file with a nested structure. This is simple and portable but doesn't scale to hundreds of pets or thousands of tasks. A proper production system would use a database. For a single-user pet care app, JSON is the right tradeoff: zero infrastructure, human-readable, and trivially version-controlled.

---

## 3. AI Collaboration

### AI Tools and Strategies

**Agent Mode (multi-file generation)** was most effective for scaffolding the initial class structure across `pawpal_system.py`, `main.py`, and `app.py` simultaneously. Asking the AI to generate all three files in one prompt ensured the interfaces were consistent — the same `Task` fields appeared in the CLI demo, the tests, and the Streamlit UI without mismatch.

**Inline Chat** was most effective for single methods — asking "write `find_next_available_slot` that avoids occupied windows and returns `None` if nothing is found in 24 hours" produced clean, focused code without affecting surrounding methods.

**Edit Mode** was helpful for the filtering logic, where I wanted to iterate on the exact lambda expression in `sort_by_priority` without rewriting the whole method. Asking the AI to "adjust the sort key so High sorts before Low but preserves time ordering within each priority tier" led directly to the `(-PRIORITY_MAP[t.priority], t.due_time)` tuple key.

**Separate chat sessions** for different subsystems kept context focused. The session for `pawpal_system.py` didn't drift into Streamlit UI concerns, and the session for `tests/test_pawpal.py` stayed focused on pytest patterns and fixture design.

### Rejected AI Suggestion

The AI suggested using SQLite (via `sqlite3`) for data persistence, arguing it would be more robust and support concurrent access. I rejected this because:

1. The project is a single-user desktop app — concurrent access is not a concern.
2. SQLite would require schema migration logic whenever the data model changes.
3. JSON is human-readable, requires no setup, and can be version-controlled naturally.
4. The assignment rubric asks for JSON serialization specifically.

I modified the suggestion to keep JSON but add explicit `datetime.isoformat()` / `datetime.fromisoformat()` handling (which the AI initially glossed over), making the serialization robust across Python versions.

The AI's instinct toward a real database was not wrong for a production system — it was wrong for *this* system. Being the lead architect meant recognizing that distinction.

### Prompt Comparison: Recurring Task Logic

I tested two approaches to `handle_recurring` with different AI models:

- **Model A** generated a version that checked frequency inside `handle_recurring` itself, duplicating the `timedelta` logic that was already in `mark_complete`. This created two places to update if the frequency rules ever changed — a classic maintainability problem.

- **Model B** (used in the final implementation) suggested the cleaner split: `mark_complete()` owns the recurrence math and *returns* the next `Task` (or `None`), while `handle_recurring()` is a thin orchestrator that calls `mark_complete()`, checks the return value, and appends to the pet. This is more modular, more Pythonic, and easier to test — `mark_complete()` can be unit-tested without a `Pet` or `Scheduler` in scope.

The key difference was modularity: Model B respected the principle that a method should do one thing. Model A conflated marking complete with scheduling the next occurrence into a single, harder-to-test function.

---

## 4. Testing and Verification

### What Was Tested

The 18-test suite in `tests/test_pawpal.py` covers every public method of every class:
- `Task.mark_complete()` — status change, daily recurrence, weekly recurrence, `once` produces `None`
- `Task.reschedule()` — due time update
- `Pet.add_task()` / `remove_task()` — count changes
- `Owner.get_all_tasks()` — aggregation across pets
- `Scheduler.sort_by_time()` — chronological order assertion
- `Scheduler.sort_by_priority()` — High-first assertion
- `Scheduler.filter_by_pet()` — pet name filtering
- `Scheduler.filter_by_status()` — pending and completed variants
- `Scheduler.detect_conflicts()` — positive and negative cases
- `Scheduler.handle_recurring()` — task addition and no-addition cases
- `Scheduler.find_next_available_slot()` — avoids busy slots
- `Scheduler.get_daily_schedule()` — date-scoping
- Edge cases: empty owner, pet with no tasks

### Confidence

**⭐⭐⭐⭐⭐** — All algorithmic paths are covered by at least one test. Fixtures use fixed datetimes to eliminate flakiness from time-dependent behavior.

Edge cases to explore next:
- Tasks spanning midnight (does `get_daily_schedule` handle `23:59` correctly?)
- Very large task sets (hundreds of tasks) to verify sort performance
- Loading a corrupted `data.json` and graceful recovery
- Recurring task chains (mark the next task complete immediately after creation)

---

## 5. Reflection

### What Went Well

The clean separation between `Task`/`Pet`/`Owner` (data) and `Scheduler` (algorithms) made both testing and the Streamlit UI integration much smoother than expected. Because `Scheduler` only reads from and writes to the owner's data through well-defined methods, the Streamlit app could simply call `scheduler.sort_by_time()` or `scheduler.detect_conflicts()` without knowing anything about the internal structure of tasks or pets.

### What I Would Improve

The conflict detection only checks exact time matches. A duration-aware overlap checker (using `[start, start + duration)` intervals) would be more realistic and catch more real scheduling problems. This would require adding `duration_minutes` to `Task`, which is a small change with significant downstream benefits.

### Key Takeaway

The most important lesson was that **AI tools are most effective when you bring a clear design first**. When I gave the AI a precise interface spec ("write `find_next_available_slot` that takes a `Pet` and `duration_minutes`, searches in 30-minute increments, and returns `None` after 24 hours"), the output was close to production-ready. When I gave vague prompts ("handle recurring tasks somehow"), the output required significant rework. The lead architect role isn't about typing code — it's about thinking through interfaces and constraints precisely enough that the AI (or any other developer) can implement them correctly.
