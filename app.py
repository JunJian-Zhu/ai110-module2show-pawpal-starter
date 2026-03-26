"""PawPal+ Streamlit UI — full pet care scheduling dashboard."""

import os
from datetime import datetime

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
STATUS_EMOJI   = {True: "✅ Done", False: "⬜ Pending"}
DATA_FILE      = "data.json"


# ── Session-state bootstrap ───────────────────────────────────────────────────
def _load_owner() -> Owner:
    """Load owner from JSON if the file exists, otherwise return a blank owner."""
    if os.path.exists(DATA_FILE):
        try:
            loaded = Owner.load_from_json(DATA_FILE)
            if loaded.name:
                return loaded
        except Exception:
            pass
    return Owner("", "")


if "owner" not in st.session_state:
    st.session_state.owner = _load_owner()


def save() -> None:
    """Persist the current owner to data.json."""
    if st.session_state.owner.name:
        st.session_state.owner.save_to_json(DATA_FILE)


# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("🐾 PawPal+")
st.sidebar.caption("Smart Pet Care Management")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Owner Setup", "🐾 Add Pet", "📋 Add Task", "📅 View Schedule", "✅ Manage Tasks"],
)

owner: Owner = st.session_state.owner

# ── Page: Owner Setup ─────────────────────────────────────────────────────────
if page == "🏠 Owner Setup":
    st.title("🏠 Owner Setup")
    with st.form("owner_form"):
        name = st.text_input("Owner Name", value=owner.name)
        contact = st.text_input("Contact Info (email/phone)", value=owner.contact_info)
        submitted = st.form_submit_button("Save Owner")
    if submitted:
        owner.name = name.strip()
        owner.contact_info = contact.strip()
        save()
        st.success(f"✅ Owner saved: {owner.name}")

    if owner.name:
        st.info(f"Current owner: **{owner.name}** — {owner.contact_info}")
        st.write(f"Pets registered: **{len(owner.pets)}**")
    else:
        st.warning("Please set an owner name to get started.")

# ── Page: Add Pet ─────────────────────────────────────────────────────────────
elif page == "🐾 Add Pet":
    st.title("🐾 Add a New Pet")
    if not owner.name:
        st.warning("Please configure an owner first (🏠 Owner Setup).")
    else:
        with st.form("pet_form"):
            pet_name    = st.text_input("Pet Name")
            species     = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
            breed       = st.text_input("Breed")
            age         = st.number_input("Age (years)", min_value=0, max_value=30, value=1)
            submitted   = st.form_submit_button("Add Pet")

        if submitted:
            if not pet_name.strip():
                st.error("Pet name cannot be empty.")
            elif any(p.name.lower() == pet_name.strip().lower() for p in owner.pets):
                st.error(f"A pet named '{pet_name}' already exists.")
            else:
                new_pet = Pet(
                    name=pet_name.strip(),
                    species=species,
                    breed=breed.strip(),
                    age=int(age),
                )
                owner.add_pet(new_pet)
                save()
                st.success(f"✅ Added {new_pet.name} ({new_pet.breed}) to {owner.name}'s household!")

        if owner.pets:
            st.subheader("Current Pets")
            for pet in owner.pets:
                st.write(f"• **{pet.name}** — {pet.species} / {pet.breed}, {pet.age} yr(s)")

# ── Page: Add Task ────────────────────────────────────────────────────────────
elif page == "📋 Add Task":
    st.title("📋 Add a New Task")
    if not owner.pets:
        st.warning("Add at least one pet before creating tasks.")
    else:
        pet_names = [p.name for p in owner.pets]
        with st.form("task_form"):
            selected_pet = st.selectbox("Assign to Pet", pet_names)
            description  = st.text_input("Task Description", placeholder="e.g. Morning walk")
            col1, col2   = st.columns(2)
            with col1:
                due_date = st.date_input("Due Date", value=datetime.now().date())
                due_time = st.time_input("Due Time", value=datetime.now().replace(minute=0, second=0).time())
            with col2:
                priority  = st.selectbox("Priority", ["High", "Medium", "Low"])
                frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
            submitted = st.form_submit_button("Add Task")

        if submitted:
            if not description.strip():
                st.error("Task description cannot be empty.")
            else:
                due_dt = datetime.combine(due_date, due_time)
                task = Task(
                    description=description.strip(),
                    due_time=due_dt,
                    frequency=frequency,
                    priority=priority,
                    pet_name=selected_pet,
                )
                pet = next(p for p in owner.pets if p.name == selected_pet)
                pet.add_task(task)

                # Immediately check for conflicts
                scheduler = Scheduler(owner)
                conflicts = scheduler.detect_conflicts()
                save()

                st.success(f"✅ Added '{task.description}' for {selected_pet}!")
                for warning in conflicts:
                    st.warning(warning)

# ── Page: View Schedule ───────────────────────────────────────────────────────
elif page == "📅 View Schedule":
    st.title("📅 Schedule View")
    if not owner.get_all_tasks():
        st.info("No tasks yet. Add some from 📋 Add Task.")
    else:
        scheduler = Scheduler(owner)

        # Conflict warnings at the top
        conflicts = scheduler.detect_conflicts()
        for w in conflicts:
            st.warning(w)

        view = st.radio("Sort by", ["🕐 Time", "⭐ Priority"], horizontal=True)
        tasks = scheduler.sort_by_time() if "Time" in view else scheduler.sort_by_priority()

        rows = []
        for task in tasks:
            rows.append({
                "Status":      STATUS_EMOJI[task.is_complete],
                "Priority":    PRIORITY_EMOJI.get(task.priority, "") + " " + task.priority,
                "Description": task.description,
                "Pet":         task.pet_name,
                "Due":         task.due_time.strftime("%b %d  %H:%M"),
                "Frequency":   task.frequency,
            })

        st.dataframe(rows, use_container_width=True)

        # Daily schedule section
        st.subheader("📆 Today's Schedule")
        today_tasks = scheduler.get_daily_schedule()
        if today_tasks:
            for task in today_tasks:
                emoji = PRIORITY_EMOJI.get(task.priority, "")
                status = "~~" if task.is_complete else ""
                st.markdown(
                    f"{STATUS_EMOJI[task.is_complete]} &nbsp; {emoji} **{task.description}** "
                    f"({task.pet_name}) — {task.due_time.strftime('%H:%M')}"
                )
        else:
            st.write("No tasks scheduled for today.")

# ── Page: Manage Tasks ────────────────────────────────────────────────────────
elif page == "✅ Manage Tasks":
    st.title("✅ Manage Tasks")
    if not owner.get_all_tasks():
        st.info("No tasks to manage yet.")
    else:
        scheduler = Scheduler(owner)

        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            pet_filter = st.selectbox(
                "Filter by pet",
                ["All pets"] + [p.name for p in owner.pets],
            )
        with col2:
            status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed"])

        tasks = owner.get_all_tasks()
        if pet_filter != "All pets":
            tasks = [t for t in tasks if t.pet_name == pet_filter]
        if status_filter == "Pending":
            tasks = [t for t in tasks if not t.is_complete]
        elif status_filter == "Completed":
            tasks = [t for t in tasks if t.is_complete]

        st.write(f"Showing **{len(tasks)}** task(s)")

        for i, task in enumerate(tasks):
            emoji = PRIORITY_EMOJI.get(task.priority, "")
            with st.expander(
                f"{emoji} {task.description}  |  {task.pet_name}  |  "
                f"{task.due_time.strftime('%b %d %H:%M')}  |  {STATUS_EMOJI[task.is_complete]}"
            ):
                st.write(f"**Frequency:** {task.frequency}")
                st.write(f"**Priority:** {task.priority}")
                st.write(f"**Due:** {task.due_time.strftime('%A, %B %d %Y at %H:%M')}")

                if not task.is_complete:
                    if st.button(f"Mark Complete", key=f"complete_{i}"):
                        pet = next((p for p in owner.pets if p.name == task.pet_name), None)
                        if pet:
                            next_task = scheduler.handle_recurring(task, pet)
                            save()
                            if next_task:
                                st.success(
                                    f"✅ Done! Next '{task.description}' scheduled for "
                                    f"{next_task.due_time.strftime('%b %d at %H:%M')}"
                                )
                            else:
                                st.success(f"✅ '{task.description}' marked complete!")
                            st.rerun()
                else:
                    st.caption("Task already completed.")

        # Find next available slot widget
        st.divider()
        st.subheader("🔍 Find Next Available Slot")
        col1, col2 = st.columns(2)
        with col1:
            slot_pet = st.selectbox("Pet", [p.name for p in owner.pets], key="slot_pet")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=240, value=30, step=5)

        if st.button("Find Slot"):
            pet = next((p for p in owner.pets if p.name == slot_pet), None)
            if pet:
                slot = scheduler.find_next_available_slot(pet, int(duration))
                if slot:
                    st.success(f"📅 Next free {duration}-min slot for {slot_pet}: **{slot.strftime('%A, %b %d at %H:%M')}**")
                else:
                    st.warning("No open slot found in the next 24 hours.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption(f"Owner: **{owner.name or 'Not set'}**")
st.sidebar.caption(f"Pets: {len(owner.pets)}  |  Tasks: {len(owner.get_all_tasks())}")
