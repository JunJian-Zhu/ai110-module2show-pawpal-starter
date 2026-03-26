"""PawPal+ CLI demo — showcases all features with formatted tables and color output."""

from datetime import datetime, timedelta

from tabulate import tabulate

from pawpal_system import Owner, Pet, Scheduler, Task

# ── Emoji helpers ─────────────────────────────────────────────────────────────
PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
STATUS_EMOJI = {True: "✅", False: "⬜"}


def fmt(task: Task) -> list:
    """Format a Task into a table row."""
    return [
        STATUS_EMOJI[task.is_complete],
        PRIORITY_EMOJI.get(task.priority, "") + " " + task.priority,
        task.description,
        task.pet_name,
        task.due_time.strftime("%b %d  %H:%M"),
        task.frequency,
    ]


HEADERS = ["Done", "Priority", "Description", "Pet", "Due", "Freq"]


def section(title: str) -> None:
    """Print a styled section header."""
    print(f"\n{'─' * 58}")
    print(f"  {title}")
    print(f"{'─' * 58}")


def print_tasks(tasks: list) -> None:
    """Print a list of tasks as a formatted table."""
    if not tasks:
        print("  (no tasks)")
        return
    rows = [fmt(t) for t in tasks]
    print(tabulate(rows, headers=HEADERS, tablefmt="rounded_outline"))


# ── Build the demo world ───────────────────────────────────────────────────────
def main() -> None:
    print("\n" + "=" * 58)
    print("  🐾  PawPal+ — Smart Pet Care Management  🐾")
    print("=" * 58)

    # Owner
    alex = Owner("Alex Rivera", "alex@pawpal.com")

    # Pets
    buddy = Pet(name="Buddy", species="dog", breed="Labrador", age=3)
    whiskers = Pet(name="Whiskers", species="cat", breed="Siamese", age=5)
    alex.add_pet(buddy)
    alex.add_pet(whiskers)

    print(f"\n👤  Owner : {alex.name}  |  📞 {alex.contact_info}")
    print(f"🐶  {buddy.name} ({buddy.breed}, {buddy.age} yrs)")
    print(f"🐱  {whiskers.name} ({whiskers.breed}, {whiskers.age} yrs)")

    # Base date – use today at fixed hours so output is deterministic
    today = datetime.now().replace(minute=0, second=0, microsecond=0)

    def t(hours_offset: float, pet_name: str, **kwargs) -> Task:
        task = Task(due_time=today + timedelta(hours=hours_offset), pet_name=pet_name, **kwargs)
        return task

    # Tasks for Buddy
    walk_am = t(8,  "Buddy", description="Morning walk",    frequency="daily",  priority="High")
    feeding = t(7,  "Buddy", description="Breakfast",        frequency="daily",  priority="High")
    grooming = t(14, "Buddy", description="Grooming session", frequency="weekly", priority="Medium")
    meds    = t(9,  "Buddy", description="Flea medication",  frequency="once",   priority="Low")

    # Tasks for Whiskers
    play    = t(10, "Whiskers", description="Playtime",       frequency="daily",  priority="Medium")
    vet     = t(11, "Whiskers", description="Vet check-up",   frequency="once",   priority="High")
    litter  = t(12, "Whiskers", description="Litter cleaning", frequency="daily",  priority="Low")

    # Conflict task — same pet, same time as walk_am
    conflict_task = t(8, "Buddy", description="Obedience training", frequency="once", priority="Medium")

    for task in [walk_am, feeding, grooming, meds]:
        buddy.add_task(task)
    for task in [play, vet, litter]:
        whiskers.add_task(task)
    # Add conflicting task last so it shows up in detection
    buddy.add_task(conflict_task)

    scheduler = Scheduler(alex)

    # ── 1. All tasks ──────────────────────────────────────────────────────────
    section("1 · All Tasks Added")
    print_tasks(alex.get_all_tasks())

    # ── 2. Sorted by time ─────────────────────────────────────────────────────
    section("2 · Sorted by Time (chronological)")
    print_tasks(scheduler.sort_by_time())

    # ── 3. Sorted by priority ─────────────────────────────────────────────────
    section("3 · Sorted by Priority (High → Low, then time)")
    print_tasks(scheduler.sort_by_priority())

    # ── 4. Filter by pet ─────────────────────────────────────────────────────
    section("4 · Filter by Pet → Buddy only")
    print_tasks(scheduler.filter_by_pet("Buddy"))

    section("4b · Filter by Pet → Whiskers only")
    print_tasks(scheduler.filter_by_pet("Whiskers"))

    # ── 5. Filter by status ───────────────────────────────────────────────────
    section("5 · Filter by Status → Pending tasks")
    print_tasks(scheduler.filter_by_status(is_complete=False))

    # ── 6. Conflict detection ─────────────────────────────────────────────────
    section("6 · Conflict Detection")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts detected.")

    # ── 7. Recurring task completion ─────────────────────────────────────────
    section("7 · Recurring Task Completion")
    print(f"  Marking '{walk_am.description}' (daily) as complete …")
    next_walk = scheduler.handle_recurring(walk_am, buddy)
    print(f"  ✅ Completed.  Next occurrence auto-created: {next_walk.due_time.strftime('%b %d  %H:%M')}")

    print(f"\n  Buddy's tasks after recurrence:")
    print_tasks(scheduler.filter_by_pet("Buddy"))

    # Filter by status — now shows completed + pending split
    section("5b · Filter by Status → Completed tasks")
    print_tasks(scheduler.filter_by_status(is_complete=True))

    # ── 8. Next available slot ────────────────────────────────────────────────
    section("8 · Next Available Slot")
    slot = scheduler.find_next_available_slot(buddy, duration_minutes=30)
    if slot:
        print(f"  📅 Next free 30-min slot for Buddy: {slot.strftime('%b %d  %H:%M')}")
    else:
        print("  No open slot found in the next 24 hours.")

    slot_w = scheduler.find_next_available_slot(whiskers, duration_minutes=45)
    if slot_w:
        print(f"  📅 Next free 45-min slot for Whiskers: {slot_w.strftime('%b %d  %H:%M')}")

    # ── 9. Weighted priority scores ────────────────────────────────────────────
    section("9 · Weighted Priority Scores (urgency × priority)")
    scored = [
        (scheduler.weighted_priority_score(task), task)
        for task in alex.get_all_tasks()
        if not task.is_complete
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    score_rows = [
        [f"{score:.2f}", PRIORITY_EMOJI.get(t.priority, "") + " " + t.priority,
         t.description, t.pet_name, t.due_time.strftime("%H:%M")]
        for score, t in scored
    ]
    print(tabulate(score_rows, headers=["Score", "Priority", "Description", "Pet", "Due"],
                   tablefmt="rounded_outline"))

    # ── 10. Daily schedule ────────────────────────────────────────────────────
    section("10 · Today's Daily Schedule (priority-first)")
    print_tasks(scheduler.get_daily_schedule())

    # ── 11. Save & reload ─────────────────────────────────────────────────────
    section("11 · Data Persistence — Save & Load")
    alex.save_to_json("data.json")
    print("  💾 Saved to data.json")

    alex2 = Owner.load_from_json("data.json")
    scheduler2 = Scheduler(alex2)
    print(f"  📂 Loaded owner: {alex2.name}  ({len(alex2.pets)} pets, "
          f"{len(alex2.get_all_tasks())} tasks)")
    print("\n  Tasks after reload:")
    print_tasks(scheduler2.sort_by_time())

    print("\n" + "=" * 58)
    print("  🎉  Demo complete — run 'streamlit run app.py' for the UI")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()
