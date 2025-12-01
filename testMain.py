import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector


# =========================================================
# DATABASE CONNECTION (EDIT THIS TO MATCH YOUR SETUP)
# =========================================================

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="mental_health_access_multistate"
    )


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def show_db_error(err):
    messagebox.showerror("Database Error", str(err))


# =========================================================
# MAIN APPLICATION
# =========================================================

class MentalHealthApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mental Health Access – Database Front End")
        self.geometry("1100x650")

        self.state_map = {}   # name -> id
        self.state_list = []  # list of (id, name)

        self._build_ui()
        self.load_states_into_memory()

    @staticmethod
    def _format_heading_text(col):
        base = col.replace("_", " ")
        text = base.title()
        return (text
                .replace("Us", "US")
                .replace("Id", "ID")
                )

    # =====================================================
    # GENERIC TREEVIEW SORTING (with ▲ / ▼ indicators)
    # =====================================================
    def _treeview_sort_column(self, tree, col, reverse):
        """
        Sort a ttk.Treeview by a given column.

        - Tries numeric sort first
        - Falls back to string (case-insensitive)
        - Clicking again toggles ascending/descending
        - Shows ▲ for ascending, ▼ for descending on the active column
        """
        # Get current data in the tree
        data = [(tree.set(item, col), item) for item in tree.get_children("")]

        def convert(value):
            try:
                v = str(value).replace(",", "")
                return float(v)
            except (ValueError, TypeError):
                return str(value).lower()

        # Sort rows
        data.sort(key=lambda t: convert(t[0]), reverse=reverse)

        # Reorder rows
        for index, (_, item) in enumerate(data):
            tree.move(item, "", index)

        # Update ALL column headings: text + click behavior
        for c in tree["columns"]:
            base_text = c.replace("_", " ").title()

            if c == col:
                # This is the column we just sorted
                arrow = " ▲" if not reverse else " ▼"
                text = base_text + arrow
                next_reverse = not reverse  # toggle on next click
            else:
                # Other columns: no arrow, reset to ascending for next click
                text = base_text
                next_reverse = False

            tree.heading(
                c,
                text=text,
                command=lambda cc=c, rr=next_reverse: self._treeview_sort_column(tree, cc, rr)
            )

    def _reset_treeview_headings(self, tree):
        """
        Remove ▲ / ▼ arrows from all column headings
        and reset click behavior to ascending sort.
        """
        for col in tree["columns"]:
            base_text = col.replace("_", " ").title()
            tree.heading(
                col,
                text=base_text,
                command=lambda c=col: self._treeview_sort_column(tree, c, False)
            )

    # -----------------------------------------------------
    # BUILD UI (TABS)
    # -----------------------------------------------------
    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Tabs
        self.tab_states = ttk.Frame(notebook)
        self.tab_metrics = ttk.Frame(notebook)
        self.tab_queries = ttk.Frame(notebook)
        self.tab_search = ttk.Frame(notebook)

        notebook.add(self.tab_states, text="States (CRUD)")
        notebook.add(self.tab_metrics, text="Crisis Metrics (CRUD)")
        notebook.add(self.tab_queries, text="Analytics / Queries")
        notebook.add(self.tab_search, text="Facility Search")

        self._build_states_tab()
        self._build_metrics_tab()
        self._build_queries_tab()
        self._build_search_tab()
        
    # =====================================================
    # SEARCH TAB
    # =====================================================
    def _build_search_tab(self):
        # form
        frame_form = ttk.LabelFrame(self.tab_search, text="Search Facilities by ZIP Code")
        frame_form.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame_form, text="State:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Label(frame_form, text="ZIP Code:").grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.zip_state_var = tk.StringVar()
        self.zip_code_var = tk.StringVar()

        self.combo_zip_state = ttk.Combobox(frame_form, textvariable=self.zip_state_var, state="readonly", width=30)
        self.combo_zip_state.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.entry_zip_code = ttk.Entry(frame_form, textvariable=self.zip_code_var, width=15)
        self.entry_zip_code.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(frame_form, text="Search", command=self.search_facilities).grid(
            row=2, column=0, columnspan=2, pady=10
        )

        # table
        frame_table = ttk.LabelFrame(self.tab_search, text="Matching Facilities")
        frame_table.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("id", "facility_name", "address", "city", "state", "zip", "phone")
        self.zip_tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=18)

        for col in columns:
            self.zip_tree.heading(
                col,
                text=self._format_heading_text(col),
                command=lambda c=col: self._treeview_sort_column(self.zip_tree, c, False)
            )
            widths = {
                "id": 60,
                "facility_name": 250,
                "address": 300,
                "city": 150,
                "state": 80,
                "zip": 100,
                "phone": 120
            }

            self.zip_tree.column(col, width=widths[col], anchor="center")

        self.zip_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.zip_tree.yview)
        self.zip_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.refresh_state_dropdowns()

    def search_facilities(self):
        state_name = self.zip_state_var.get().strip()
        zip_code = self.zip_code_var.get().strip()

        if not state_name or not zip_code:
            messagebox.showwarning("Validation", "Please select a state and enter a ZIP code.")
            return

        state_id = self.state_map.get(state_name)
        if not state_id:
            messagebox.showerror("Error", "Selected state not found in memory.")
            return

        for row in self.zip_tree.get_children():
            self.zip_tree.delete(row)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            query = """
                SELECT facility_id,
                    facility_name,
                    CONCAT(street1, ' ', IFNULL(street2, '')) AS address,
                    city,
                    state_id,
                    (SELECT state_name FROM state_summary WHERE state_id = mh.state_id) AS state,
                    zip,
                    phone_number
                FROM mental_health_facilities mh
                WHERE state_id = %s AND zip = %s
            """
            cur.execute(query, (state_id, zip_code))
            facilities = cur.fetchall()
            cur.close()
            conn.close()

            if not facilities:
                messagebox.showinfo("No Results", f"No facilities found with ZIP code {zip_code}.")
                return

            for fac in facilities:
                self.zip_tree.insert("", "end", values=(
                    fac['facility_id'],
                    fac['facility_name'],
                    fac['address'],
                    fac['city'],
                    fac['state'],
                    fac['zip'],
                    fac.get('phone_number', '')
                ))

        except Exception as e:
            show_db_error(e)

    # =====================================================
    # STATES TAB  (CRUD FOR state_summary)
    # =====================================================
    # =====================================================
    # STATES TAB  (CRUD FOR state_summary)
    # =====================================================
    def _build_states_tab(self):
        frame_form = ttk.LabelFrame(self.tab_states, text="State Details")
        frame_form.pack(fill="x", padx=10, pady=10)

        # form fields
        ttk.Label(frame_form, text="ID (auto-generated):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Label(frame_form, text="State Name:").grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.state_id_var = tk.StringVar()
        self.state_name_var = tk.StringVar()

        self.entry_state_id = ttk.Label(frame_form, textvariable=self.state_id_var)
        self.entry_state_id.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.entry_state_name = ttk.Entry(frame_form, textvariable=self.state_name_var, width=40)
        self.entry_state_name.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # buttons
        frame_buttons = ttk.Frame(frame_form)
        frame_buttons.grid(row=2, column=0, columnspan=2, pady=5)

        ttk.Button(frame_buttons, text="Add New", command=self.add_state).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Update", command=self.update_state).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Delete", command=self.delete_state).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Clear Form", command=self.clear_state_form).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Refresh Table", command=self.load_states_table).pack(side="left", padx=5)

        # table
        frame_table = ttk.LabelFrame(self.tab_states, text="States")
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("state_id", "state_name")
        self.states_tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=15)

        for col in columns:
            self.states_tree.heading(
                col,
                text=self._format_heading_text(col),
                command=lambda c=col: self._treeview_sort_column(self.states_tree, c, False)
            )
            self.states_tree.column(
                col,
                width=200 if col == "state_name" else 80,
                anchor="center"
            )

        self.states_tree.pack(fill="both", expand=True, side="left")

        self.states_tree.bind("<<TreeviewSelect>>", self.on_state_row_select)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.states_tree.yview)
        self.states_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # *** This is what actually loads the data ***
        self.load_states_table()

    # ----------------- STATES CRUD METHODS ----------------
    def load_states_table(self):
        """Load states into the table and into memory."""
        # Clear existing rows
        for row in self.states_tree.get_children():
            self.states_tree.delete(row)

        self._reset_treeview_headings(self.states_tree)

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT state_id, state_name FROM state_summary ORDER BY state_name")
            rows = cur.fetchall()
        except Exception as e:
            show_db_error(e)
            return
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass

        # store in memory
        self.state_list = rows[:]
        self.state_map = {name: sid for sid, name in rows}

        # actually insert into the Treeview
        for sid, name in rows:
            self.states_tree.insert("", "end", values=(sid, name))

        # also refresh state dropdowns in other tabs if built
        self.refresh_state_dropdowns()

    def clear_state_form(self):
        self.state_id_var.set("")
        self.state_name_var.set("")

    def on_state_row_select(self, event):
        selected = self.states_tree.selection()
        if not selected:
            return
        values = self.states_tree.item(selected[0], "values")
        if values:
            self.state_id_var.set(values[0])
            self.state_name_var.set(values[1])

    def add_state(self):
        name = self.state_name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "State name is required.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO state_summary (state_name) VALUES (%s)", (name,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        self.clear_state_form()
        self.load_states_table()
        messagebox.showinfo("Success", f"State '{name}' added.")

    def update_state(self):
        sid = self.state_id_var.get()
        if not sid:
            messagebox.showwarning("Validation", "Select a state to update.")
            return

        name = self.state_name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "State name is required.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE state_summary SET state_name = %s WHERE state_id = %s", (name, sid))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        self.load_states_table()
        messagebox.showinfo("Success", "State updated.")

    def delete_state(self):
        sid = self.state_id_var.get()
        if not sid:
            messagebox.showwarning("Validation", "Select a state to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete this state? (Make sure there are no dependent rows.)"):
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM state_summary WHERE state_id = %s", (sid,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        self.clear_state_form()
        self.load_states_table()
        messagebox.showinfo("Success", "State deleted.")

    # =====================================================
    # METRICS TAB  (CRUD FOR crisis_response_services)
    # =====================================================
    def _build_metrics_tab(self):
        # form
        frame_form = ttk.LabelFrame(self.tab_metrics, text="Crisis Metric Details")
        frame_form.pack(fill="x", padx=10, pady=10)

        labels = [
            "ID (auto-generated):", "State:", "Metric Name:",
            "US Value:", "State Value:"
        ]
        for i, text in enumerate(labels):
            ttk.Label(frame_form, text=text).grid(row=i, column=0, padx=5, pady=3, sticky="e")

        self.metric_id_var = tk.StringVar()
        self.metric_state_var = tk.StringVar()
        self.metric_name_var = tk.StringVar()
        self.metric_us_var = tk.StringVar()
        self.metric_state_val_var = tk.StringVar()

        self.entry_metric_id = ttk.Label(frame_form, textvariable=self.metric_id_var)
        self.entry_metric_id.grid(row=0, column=1, padx=5, pady=3, sticky="w")

        self.combo_metric_state = ttk.Combobox(frame_form, textvariable=self.metric_state_var, state="readonly", width=30)
        self.combo_metric_state.grid(row=1, column=1, padx=5, pady=3, sticky="w")

        self.entry_metric_name = ttk.Entry(frame_form, textvariable=self.metric_name_var, width=40)
        self.entry_metric_name.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        self.entry_metric_us = ttk.Entry(frame_form, textvariable=self.metric_us_var, width=15)
        self.entry_metric_us.grid(row=3, column=1, padx=5, pady=3, sticky="w")

        self.entry_metric_state_val = ttk.Entry(frame_form, textvariable=self.metric_state_val_var, width=15)
        self.entry_metric_state_val.grid(row=4, column=1, padx=5, pady=3, sticky="w")

        # buttons
        frame_buttons = ttk.Frame(frame_form)
        frame_buttons.grid(row=6, column=0, columnspan=2, pady=5)

        ttk.Button(frame_buttons, text="Add Metric", command=self.add_metric).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Update Metric", command=self.update_metric).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Delete Metric", command=self.delete_metric).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Clear Form", command=self.clear_metric_form).pack(side="left", padx=5)
        ttk.Button(frame_buttons, text="Refresh Table", command=self.load_metrics_table).pack(side="left", padx=5)

        # table
        frame_table = ttk.LabelFrame(self.tab_metrics, text="Crisis Response Metrics")
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "state_name", "metric", "us_value", "state_value")
        self.metrics_tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=15)
        for col in columns:
            self.metrics_tree.heading(
                col,
                text=self._format_heading_text(col),
                command=lambda c=col: self._treeview_sort_column(self.metrics_tree, c, False)
            )
            width = 80
            if col == "state_name":
                width = 150
            elif col == "metric":
                width = 250
            self.metrics_tree.column(col, width=width, anchor="center")
        self.metrics_tree.pack(side="left", fill="both", expand=True)

        self.metrics_tree.bind("<<TreeviewSelect>>", self.on_metric_row_select)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.metrics_tree.yview)
        self.metrics_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.load_metrics_table()

    # --------------- METRICS CRUD METHODS ----------------
    def load_metrics_table(self):
        for row in self.metrics_tree.get_children():
            self.metrics_tree.delete(row)

        self._reset_treeview_headings(self.states_tree)

        try:
            conn = get_connection()
            cur = conn.cursor()
            # assume table structure: id, state_id, metric, us_value, state_value
            query = """
                SELECT c.id,
                       s.state_name,
                       c.metric,
                       c.us_value,
                       c.state_value
                FROM crisis_response_services c
                JOIN state_summary s ON c.state_id = s.state_id
                ORDER BY s.state_name, c.metric
            """
            cur.execute(query)
            rows = cur.fetchall()
            self.metric_names = sorted({row[2] for row in rows})
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        for row in rows:
            self.metrics_tree.insert("", "end", values=row)

    def clear_metric_form(self):
        self.metric_id_var.set("")
        self.metric_state_var.set("")
        self.metric_name_var.set("")
        self.metric_us_var.set("")
        self.metric_state_val_var.set("")

    def on_metric_row_select(self, event):
        selected = self.metrics_tree.selection()
        if not selected:
            return
        values = self.metrics_tree.item(selected[0], "values")
        if values:
            self.metric_id_var.set(values[0])
            self.metric_state_var.set(values[1])
            self.metric_name_var.set(values[2])
            self.metric_us_var.set(values[3])
            self.metric_state_val_var.set(values[4])

    def add_metric(self):
        state_name = self.metric_state_var.get()
        metric = self.metric_name_var.get().strip()
        us_val = self.metric_us_var.get().strip()
        st_val = self.metric_state_val_var.get().strip()

        if not state_name or not metric:
            messagebox.showwarning("Validation", "State and metric name are required.")
            return

        try:
            state_id = self.state_map[state_name]
        except KeyError:
            messagebox.showerror("Error", "Selected state not found in memory.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            query = """
                INSERT INTO crisis_response_services
                    (state_id, metric, us_value, state_value)
                VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(query, (state_id, us_val or None, st_val or None, metric))
        except mysql.connector.errors.ProgrammingError:
            # if column order in your DB is different, use this safer version:
            conn.rollback()
            try:
                query = """
                    INSERT INTO crisis_response_services
                        (state_id, metric, us_value, state_value)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cur.execute(query, (state_id, metric, us_val or None, st_val or None))
            except Exception as e2:
                show_db_error(e2)
                conn.close()
                return
        except Exception as e:
            show_db_error(e)
            return
        else:
            conn.commit()
            cur.close()
            conn.close()

        self.clear_metric_form()
        self.load_metrics_table()
        messagebox.showinfo("Success", "Metric added.")

    def update_metric(self):
        mid = self.metric_id_var.get()
        if not mid:
            messagebox.showwarning("Validation", "Select a metric to update.")
            return

        state_name = self.metric_state_var.get()
        metric = self.metric_name_var.get().strip()
        us_val = self.metric_us_var.get().strip()
        st_val = self.metric_state_val_var.get().strip()

        if not state_name or not metric:
            messagebox.showwarning("Validation", "State and metric name are required.")
            return

        state_id = self.state_map.get(state_name)
        if not state_id:
            messagebox.showerror("Error", "Selected state not found in memory.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            query = """
                UPDATE crisis_response_services
                SET state_id = %s,
                    metric = %s,
                    us_value = %s,
                    state_value = %s
                WHERE id = %s
            """
            cur.execute(query, (state_id, metric, us_val or None, st_val or None, mid))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        self.load_metrics_table()
        messagebox.showinfo("Success", "Metric updated.")

    def delete_metric(self):
        mid = self.metric_id_var.get()
        if not mid:
            messagebox.showwarning("Validation", "Select a metric to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete this metric?"):
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM crisis_response_services WHERE id = %s", (mid,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)
            return

        self.clear_metric_form()
        self.load_metrics_table()
        messagebox.showinfo("Success", "Metric deleted.")

    # =====================================================
    # ANALYTICAL QUERIES TAB
    # =====================================================
    def _build_queries_tab(self):
        container = ttk.Frame(self.tab_queries)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Top: frames with query controls
        frame_controls = ttk.Frame(container)
        frame_controls.pack(fill="x", side="top")

        # Bottom: shared results table
        self.frame_results = ttk.LabelFrame(container, text="Query Results")
        self.frame_results.pack(fill="both", expand=True, pady=(10, 0))

        self.query_tree = ttk.Treeview(self.frame_results, show="headings")
        self.query_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.frame_results, orient="vertical", command=self.query_tree.yview)
        self.query_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # ---------- Query 1 ----------
        q1 = ttk.LabelFrame(frame_controls, text="Q1: States where value is WORSE than US for a metric.")
        q1.pack(fill="x", pady=3)

        ttk.Label(q1, text="Metric Name:").pack(side="left", padx=5)

        self.q1_metric_var = tk.StringVar()
        self.q1_metric_combo = ttk.Combobox(
            q1,
            textvariable=self.q1_metric_var,
            state="readonly",
            width=30
        )
        self.q1_metric_combo.pack(side="left", padx=5)
        self.q1_metric_combo["values"] = self.metric_names  # <-- LIST OF METRICS

        ttk.Button(q1, text="Run", command=self.run_query1).pack(side="left", padx=5)

        # ---------- Query 2 ----------
        q2 = ttk.LabelFrame(frame_controls, text="Q2: States where value is BETTER than US for a metric.")
        q2.pack(fill="x", pady=3)

        ttk.Label(q2, text="Metric Name:").pack(side="left", padx=5)

        self.q2_metric_var = tk.StringVar()
        self.q2_metric_combo = ttk.Combobox(
            q2,
            textvariable=self.q2_metric_var,
            state="readonly",
            width=30
        )
        self.q2_metric_combo.pack(side="left", padx=5)
        self.q2_metric_combo["values"] = self.metric_names

        ttk.Button(q2, text="Run", command=self.run_query2).pack(side="left", padx=5)

        # ---------- Query 3 ----------
        q3 = ttk.LabelFrame(
            frame_controls,
            text="Q3: Top 5 metrics where a state performs WORSE than the US."
        )
        q3.pack(fill="x", pady=3)

        ttk.Label(q3, text="State:").pack(side="left", padx=5)
        self.q3_state_var = tk.StringVar()
        self.q3_state_combo = ttk.Combobox(q3, textvariable=self.q3_state_var, state="readonly", width=25)
        self.q3_state_combo.pack(side="left", padx=5)

        ttk.Button(q3, text="Run", command=self.run_query3).pack(side="left", padx=5)

        # ---------- Query 4 ----------
        q4 = ttk.LabelFrame(frame_controls, text="Q4: States that outperform the US on average (aggregated across all metrics) by more than __. (including +/-)")
        q4.pack(fill="x", pady=3)

        ttk.Label(q4, text="Gap Threshold:").pack(side="left", padx=5)
        self.q4_thresh_var = tk.StringVar(value="0")
        ttk.Entry(q4, textvariable=self.q4_thresh_var, width=10).pack(side="left", padx=5)

        ttk.Button(q4, text="Run", command=self.run_query4).pack(side="left", padx=5)

        # ---------- Query 5 ----------
        q5 = ttk.LabelFrame(frame_controls, text="Q5: Show states that perform worse than the US on at least N metrics (with details).")
        q5.pack(fill="x", pady=3)

        ttk.Label(q5, text="N (minimum metrics):").pack(side="left", padx=5)
        self.q5_n_var = tk.StringVar(value="1")
        ttk.Entry(q5, textvariable=self.q5_n_var, width=10).pack(side="left", padx=5)

        ttk.Button(q5, text="Run", command=self.run_query5).pack(side="left", padx=5)

    # -- Helper to reload state dropdowns used in other tabs/queries ---
    def load_states_into_memory(self):
        """Called at startup, then load_states_table will refresh, too."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT state_id, state_name FROM state_summary ORDER BY state_name")
            self.state_list = cur.fetchall()
            self.state_map = {name: sid for sid, name in self.state_list}
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)

        self.refresh_state_dropdowns()

    def refresh_state_dropdowns(self):
        names = [name for _, name in self.state_list]
        if hasattr(self, "combo_metric_state"):
            self.combo_metric_state["values"] = names
        if hasattr(self, "q3_state_combo"):
            self.q3_state_combo["values"] = names
        if hasattr(self, "combo_zip_state"):
            self.combo_zip_state["values"] = names

    # ---------------- QUERY TABLE UTIL --------------------
    def _display_query_results(self, cursor, title=None, sortable=True):
        # 1) Optional: update the "Query Results" header text
        if hasattr(self, "frame_results"):
            if title:
                self.frame_results.config(text=title)
            else:
                self.frame_results.config(text="Query Results")

        # 2) Fetch all rows ONCE
        rows = cursor.fetchall()

        # 3) Clear existing columns and rows
        self.query_tree.delete(*self.query_tree.get_children())
        self.query_tree["columns"] = ()

        # 4) Build columns from cursor.description (still valid after fetchall)
        col_names = [desc[0] for desc in cursor.description]
        self.query_tree["columns"] = col_names

        for col in col_names:
            heading_text = col.replace("_", " ").title()

            if sortable:
                # normal behavior: clickable, sortable columns
                cmd = lambda c=col: self._treeview_sort_column(self.query_tree, c, False)
            else:
                # for Q3: disable sorting (click does nothing)
                cmd = lambda: None

            self.query_tree.heading(
                col,
                text=heading_text,
                command=cmd
            )
            self.query_tree.column(col, anchor="center", width=150)

        # 5) Insert all rows
        for row in rows:
            self.query_tree.insert("", "end", values=row)

    # ------------------- QUERY 1 --------------------------
    def run_query1(self):
        metric = self.q1_metric_var.get().strip()
        if not metric:
            messagebox.showwarning("Validation", "Enter a metric name.")
            return

        query = """
            SELECT s.state_name,
                   c.metric,
                   c.us_value,
                   c.state_value,
                   (c.state_value - c.us_value) AS diff
            FROM crisis_response_services c
            JOIN state_summary s ON c.state_id = s.state_id
            WHERE c.metric = %s
              AND c.state_value < c.us_value
            ORDER BY diff DESC
        """

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, (metric,))
            self._display_query_results(cur)
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)

        self._display_query_results(
            cur,"Query Results – Q1: States where value is WORSE than US for a metric."
        )

    # ------------------- QUERY 2 --------------------------
    def run_query2(self):
        metric = self.q2_metric_var.get()

        if not metric:
            messagebox.showwarning("Validation", "Select a metric name.")
            return

        # Clean metric (in case it's accidentally a tuple)
        if isinstance(metric, tuple):
            metric = metric[0]

        query = """
            SELECT s.state_name,
                   c.metric,
                   c.us_value,
                   c.state_value,
                   (c.state_value - c.us_value) AS diff
            FROM crisis_response_services c
            JOIN state_summary s ON c.state_id = s.state_id
            WHERE c.metric = %s
              AND c.state_value > c.us_value
            ORDER BY diff DESC
        """

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, (metric,))  # exactly one %s
            self._display_query_results(cur)
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)

        self._display_query_results(
            cur,"Query Results – Q2: States where value is BETTER than US for a metric."
        )

    # ------------------- QUERY 3 --------------------------
    def run_query3(self):
        state_name = self.q3_state_var.get().strip()
        if not state_name:
            messagebox.showwarning("Validation", "Select a state.")
            return

        state_id = self.state_map.get(state_name)
        if not state_id:
            messagebox.showerror("Error", "State not found in memory.")
            return

        # New Q3:
        # Top 5 metrics where this state is WORSE than the US
        # diff = state_value - us_value (more negative = worse)
        query = """
            SELECT c.metric,
                   c.us_value,
                   c.state_value,
                   (c.state_value - c.us_value) AS diff
            FROM crisis_response_services c
            WHERE c.state_id = %s
              AND c.state_value < c.us_value
            ORDER BY diff ASC
            LIMIT 5
        """

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, (state_id,))
            self._display_query_results(
                cur,
                f"Query Results – Q3: Top 5 metrics where {state_name} is worse than the US.",
                sortable=False  # disable manual sorting for this query
            )
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)

    # ------------------- QUERY 4 --------------------------
    def run_query4(self):
        try:
            thresh = float(self.q4_thresh_var.get())
        except ValueError:
            messagebox.showwarning("Validation", "Gap threshold must be a number.")
            return

        query = """
            SELECT s.state_name,
                   AVG(c.state_value - c.us_value) AS avg_gap
            FROM crisis_response_services c
            JOIN state_summary s ON c.state_id = s.state_id
            GROUP BY s.state_id, s.state_name
            HAVING avg_gap > %s
            ORDER BY avg_gap DESC
        """

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, (thresh,))
            self._display_query_results(cur)
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)

        self._display_query_results(
            cur,f"Query Results – Q4: States that outperform the US on average by more than {thresh}."
        )

    # ------------------- QUERY 5 --------------------------
    def run_query5(self):
        try:
            n = int(self.q5_n_var.get())
        except ValueError:
            messagebox.showwarning("Validation", "N must be an integer.")
            return

        # Step 1: Find states with >= N worse-than-US metrics
        # Step 2: Return *detailed* metric rows for those states
        query = """
            SELECT s.state_name,
                   c.metric,
                   c.us_value,
                   c.state_value,
                   (c.state_value - c.us_value) AS gap
            FROM crisis_response_services c
            JOIN state_summary s ON c.state_id = s.state_id
            WHERE c.state_value < c.us_value
              AND c.state_id IN (
                    SELECT c2.state_id
                    FROM crisis_response_services c2
                    WHERE c2.state_value < c2.us_value
                    GROUP BY c2.state_id
                    HAVING COUNT(*) >= %s
              )
            ORDER BY s.state_name ASC, gap ASC
        """

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(query, (n,))
            self._display_query_results(
                cur,
                f"Query Results – Q5: States that perform worse than the US on at least {n} metrics (with details)."
            )
            cur.close()
            conn.close()
        except Exception as e:
            show_db_error(e)


def bring_to_front():
    # Make sure the window is visible
    app.deiconify()
    app.update_idletasks()

    # Raise it above other windows
    app.lift()
    app.attributes('-topmost', True)

    # Give it keyboard focus
    app.focus_force()

    # Let it behave normally again after a moment
    app.after(200, lambda: app.attributes('-topmost', False))






# =========================================================
# RUN THE APP
# =========================================================

if __name__ == "__main__":
    app = MentalHealthApp()
    # Schedule this to run *after* Tkinter has started its loop
    app.attributes('-fullscreen', True)
    app.after(100, bring_to_front)
    app.mainloop()
