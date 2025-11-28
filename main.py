import tkinter as tk
from tkinter import ttk

# this is a recent version as a mock without  using the actually sql database,
# for sake of production and video updates, this is not final

# MOCK DATA -------------------------------------------------------------------

MOCK_STATES = [
    (1, "Texas"),
    (2, "Alabama"),
    (3, "California"),
    (4, "New York"),
    (5, "Florida")
]

MOCK_CRS_METRICS = {
    1: [("Access to Crisis Hotline (%)", 87.5, 84.9, "Texas mock.")],
    2: [("Access to Crisis Hotline (%)", 87.5, 86.6, "Alabama mock.")],
    3: [("Access to Crisis Hotline (%)", 87.5, 88.4, "California mock.")],
    4: [("Access to Crisis Hotline (%)", 87.5, 90.1, "New York mock.")],
    5: [("Access to Crisis Hotline (%)", 87.5, 91.9, "Florida mock.")]
}


# LOGIC -------------------------------------------------------------------

def load_states():
    """Return list of states (id, name)."""
    return MOCK_STATES


def fetch_metrics():
    """Load metrics associated with the selected state."""
    state_name = state_var.get()
    if not state_name:
        return

    state_id = state_map[state_name]
    data = MOCK_CRS_METRICS.get(state_id, [])

    # Clear table
    for item in metrics_tree.get_children():
        metrics_tree.delete(item)

    # Insert mock rows
    for row in data:
        metrics_tree.insert("", "end", values=row)


# TKINTER UI -------------------------------------------------------------------

root = tk.Tk()
root.attributes('-fullscreen', True)
root.title("Mental Health Access Viewer (UI Test)")
root.geometry("900x500")

# top frame
frame_top = tk.Frame(root)
frame_top.pack(fill="x", padx=10, pady=10)

tk.Label(frame_top, text="Select State:").pack(side="left")

state_var = tk.StringVar()
state_dropdown = ttk.Combobox(frame_top, textvariable=state_var, state="readonly")
state_dropdown.pack(side="left", padx=10)

# load mock states
states = load_states()
state_map = {name: sid for sid, name in states}
state_dropdown["values"] = [name for _, name in states]

# button
tk.Button(frame_top, text="Load Metrics", command=fetch_metrics).pack(side="left")

# table
columns = ("Metric", "US Value", "State Value", "Notes")
metrics_tree = ttk.Treeview(root, columns=columns, show="headings", height=20)
metrics_tree.pack(fill="both", expand=True, padx=10, pady=10)

for col in columns:
    metrics_tree.heading(col, text=col)
    metrics_tree.column(col, width=180)


def bring_to_front():
    # Make sure the window is visible
    root.deiconify()
    root.update_idletasks()

    # Raise it above other windows
    root.lift()
    root.attributes('-topmost', True)

    # Give it keyboard focus
    root.focus_force()

    # Let it behave normally again after a moment
    root.after(200, lambda: root.attributes('-topmost', False))


# Schedule this to run *after* Tkinter has started its loop
root.after(100, bring_to_front)


root.mainloop()
