import tkinter as tk
from tkinter import ttk
import mysql.connector

#

# -------------------------------------------------------------------
# DATABASE CONNECTION
# -------------------------------------------------------------------
# Note password has been editted for privacy,
# this should be  editted to fit your sql host
# This originally fitted Harith's
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=""
        database="mental_health_access_multistate"
    )


# -------------------------------------------------------------------
# LOAD STATES INTO DROPDOWN
# -------------------------------------------------------------------
def load_states():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT state_id, state_name FROM state_summary ORDER BY state_name")
    states = cursor.fetchall()
    cursor.close()
    conn.close()
    return states


# -------------------------------------------------------------------
# QUERY METRICS FOR A SELECTED STATE
# -------------------------------------------------------------------
def fetch_metrics():
    state_name = state_var.get()
    if not state_name:
        return

    # find state_id
    state_id = state_map[state_name]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT metric, us_value, state_value, notes
        FROM crisis_response_services
        WHERE state_id = %s
    """
    cursor.execute(query, (state_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # update UI table
    for r in metrics_tree.get_children():
        metrics_tree.delete(r)

    for metric, us_val, st_val, notes in rows:
        metrics_tree.insert("", "end", values=(metric, us_val, st_val, notes))


# -------------------------------------------------------------------
# MAIN TKINTER UI
# -------------------------------------------------------------------
root = tk.Tk()
root.title("Mental Health Access – State Viewer")
root.geometry("900x500")

# frame for selecting state
frame_top = tk.Frame(root)
frame_top.pack(fill="x", padx=10, pady=10)

tk.Label(frame_top, text="Select State:").pack(side="left")

state_var = tk.StringVar()
state_dropdown = ttk.Combobox(frame_top, textvariable=state_var, state="readonly")
state_dropdown.pack(side="left", padx=10)

# load states from DB
state_list = load_states()
state_map = {name: _id for _id, name in state_list}
state_dropdown["values"] = [name for _, name in state_list]

# fetch button
tk.Button(frame_top, text="Load Metrics", command=fetch_metrics).pack(side="left")

# -------------------------------------------------------------------
# METRICS TABLE
# -------------------------------------------------------------------
columns = ("Metric", "US Value", "State Value", "Notes")
metrics_tree = ttk.Treeview(root, columns=columns, show="headings", height=20)
metrics_tree.pack(fill="both", expand=True, padx=10, pady=10)

for col in columns:
    metrics_tree.heading(col, text=col)
    metrics_tree.column(col, width=150)

root.mainloop()
