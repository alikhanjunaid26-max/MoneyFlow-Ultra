import sqlite3
import csv
import os
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup


APP_NAME = "MoneyFlow Ultra Pro Max"
DB_FILE = "moneyflow.db"


# ---------------- DATABASE ----------------

class Database:
    def __init__(self):
        self.db = sqlite3.connect(DB_FILE)
        self.create_tables()

    def create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT,
                date TEXT NOT NULL
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                amount REAL NOT NULL
            )
        """)

        self.db.commit()

    def add_transaction(self, kind, amount, category, note):
        self.db.execute(
            """
            INSERT INTO transactions
            (kind, amount, category, note, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                kind,
                amount,
                category,
                note,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )
        self.db.commit()

    def get_transactions(self):
        return self.db.execute(
            """
            SELECT id, kind, amount, category, note, date
            FROM transactions
            ORDER BY id DESC
            """
        ).fetchall()

    def delete_transaction(self, transaction_id):
        self.db.execute(
            "DELETE FROM transactions WHERE id=?",
            (transaction_id,)
        )
        self.db.commit()

    def totals(self):
        income = self.db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE kind='Income'"
        ).fetchone()[0]

        expense = self.db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE kind='Expense'"
        ).fetchone()[0]

        return income, expense, income - expense

    def category_totals(self):
        return self.db.execute("""
            SELECT category, SUM(amount)
            FROM transactions
            WHERE kind='Expense'
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """).fetchall()

    def set_budget(self, category, amount):
        self.db.execute("""
            INSERT OR REPLACE INTO budgets(category, amount)
            VALUES (?, ?)
        """, (category, amount))
        self.db.commit()

    def get_budgets(self):
        return self.db.execute(
            "SELECT category, amount FROM budgets ORDER BY category"
        ).fetchall()

    def export_csv(self, path):
        rows = self.get_transactions()

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "ID",
                "Type",
                "Amount",
                "Category",
                "Note",
                "Date"
            ])

            writer.writerows(rows)


# ---------------- UI HELPERS ----------------

def title(text, size=25):
    return Label(
        text=text,
        font_size=dp(size),
        bold=True,
        size_hint_y=None,
        height=dp(55)
    )


def make_button(text, height=52):
    return Button(
        text=text,
        font_size=dp(17),
        size_hint_y=None,
        height=dp(height)
    )


# ---------------- DASHBOARD ----------------

class Dashboard(Screen):

    def on_pre_enter(self):
        self.refresh()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        self.add_widget(self.layout)

        self.balance = Label(
            text="₹ 0.00",
            font_size=dp(38),
            bold=True,
            size_hint_y=None,
            height=dp(80)
        )

        self.income = Label(
            text="Income: ₹0.00",
            font_size=dp(18),
            size_hint_y=None,
            height=dp(40)
        )

        self.expense = Label(
            text="Expenses: ₹0.00",
            font_size=dp(18),
            size_hint_y=None,
            height=dp(40)
        )

        self.layout.add_widget(title("💰 MONEYFLOW", 28))
        self.layout.add_widget(self.balance)
        self.layout.add_widget(self.income)
        self.layout.add_widget(self.expense)

        self.layout.add_widget(
            make_button("➕ Add Transaction")
        )
        self.layout.children[0].bind(
            on_release=lambda x: self.go("add")
        )

        btn_history = make_button("📜 Transactions")
        btn_history.bind(
            on_release=lambda x: self.go("history")
        )
        self.layout.add_widget(btn_history)

        btn_reports = make_button("📊 Reports")
        btn_reports.bind(
            on_release=lambda x: self.go("reports")
        )
        self.layout.add_widget(btn_reports)

        btn_budget = make_button("🎯 Budgets")
        btn_budget.bind(
            on_release=lambda x: self.go("budget")
        )
        self.layout.add_widget(btn_budget)

        btn_settings = make_button("⚙️ Settings")
        btn_settings.bind(
            on_release=lambda x: self.go("settings")
        )
        self.layout.add_widget(btn_settings)

    def go(self, screen):
        self.manager.current = screen

    def refresh(self):
        income, expense, balance = App.get_running_app().db.totals()

        self.balance.text = f"₹ {balance:,.2f}"
        self.income.text = f"💵 Income: ₹ {income:,.2f}"
        self.expense.text = f"💸 Expenses: ₹ {expense:,.2f}"


# ---------------- ADD TRANSACTION ----------------

class AddTransaction(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        self.add_widget(layout)

        layout.add_widget(title("➕ Add Transaction"))

        self.kind = Spinner(
            text="Expense",
            values=("Expense", "Income"),
            size_hint_y=None,
            height=dp(50)
        )

        self.amount = TextInput(
            hint_text="Amount ₹",
            input_filter="float",
            multiline=False,
            font_size=dp(18),
            size_hint_y=None,
            height=dp(55)
        )

        self.category = Spinner(
            text="Food",
            values=(
                "Food",
                "Travel",
                "Shopping",
                "Bills",
                "Education",
                "Health",
                "Entertainment",
                "Salary",
                "Business",
                "Other"
            ),
            size_hint_y=None,
            height=dp(50)
        )

        self.note = TextInput(
            hint_text="Note",
            multiline=False,
            font_size=dp(17),
            size_hint_y=None,
            height=dp(55)
        )

        layout.add_widget(self.kind)
        layout.add_widget(self.amount)
        layout.add_widget(self.category)
        layout.add_widget(self.note)

        save = make_button("💾 SAVE TRANSACTION")
        save.bind(on_release=self.save)
        layout.add_widget(save)

        back = make_button("⬅ Back")
        back.bind(
            on_release=lambda x: self.go("dashboard")
        )
        layout.add_widget(back)

    def save(self, instance):

        try:
            amount = float(self.amount.text)

            if amount <= 0:
                raise ValueError

        except ValueError:
            self.popup("Enter a valid amount.")
            return

        App.get_running_app().db.add_transaction(
            self.kind.text,
            amount,
            self.category.text,
            self.note.text
        )

        self.amount.text = ""
        self.note.text = ""

        self.popup("Transaction saved successfully! 💰")

    def popup(self, message):
        Popup(
            title="MoneyFlow",
            content=Label(text=message),
            size_hint=(0.8, 0.3)
        ).open()

    def go(self, screen):
        self.manager.current = screen


# ---------------- HISTORY ----------------

class History(Screen):

    def on_pre_enter(self):
        self.refresh()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.layout = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        self.add_widget(self.layout)

        self.layout.add_widget(
            title("📜 Transactions")
        )

        scroll = ScrollView()

        self.list_layout = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        self.list_layout.bind(
            minimum_height=self.list_layout.setter("height")
        )

        scroll.add_widget(self.list_layout)

        self.layout.add_widget(scroll)

        back = make_button("⬅ Dashboard")
        back.bind(
            on_release=lambda x: self.go("dashboard")
        )

        self.layout.add_widget(back)

    def refresh(self):

        self.list_layout.clear_widgets()

        rows = App.get_running_app().db.get_transactions()

        if not rows:
            self.list_layout.add_widget(
                Label(
                    text="No transactions yet.",
                    size_hint_y=None,
                    height=dp(60)
                )
            )
            return

        for row in rows:

            transaction_id, kind, amount, category, note, date = row

            sign = "+" if kind == "Income" else "-"

            text = (
                f"{sign} ₹{amount:,.2f}\n"
                f"{category} • {note or 'No note'}\n"
                f"{date}"
            )

            box = BoxLayout(
                size_hint_y=None,
                height=dp(100),
                spacing=dp(5)
            )

            label = Label(
                text=text,
                halign="left"
            )

            delete = Button(
                text="🗑",
                size_hint_x=None,
                width=dp(65)
            )

            delete.bind(
                on_release=lambda btn, tid=transaction_id:
                self.delete(tid)
            )

            box.add_widget(label)
            box.add_widget(delete)

            self.list_layout.add_widget(box)

    def delete(self, transaction_id):

        App.get_running_app().db.delete_transaction(
            transaction_id
        )

        self.refresh()

    def go(self, screen):
        self.manager.current = screen


# ---------------- REPORTS ----------------

class Reports(Screen):

    def on_pre_enter(self):
        self.refresh()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(8)
        )

        self.add_widget(layout)

        layout.add_widget(
            title("📊 Reports")
        )

        self.report = Label(
            text="",
            font_size=dp(17)
        )

        layout.add_widget(self.report)

        back = make_button("⬅ Dashboard")
        back.bind(
            on_release=lambda x:
            self.go("dashboard")
        )

        layout.add_widget(back)

    def refresh(self):

        db = App.get_running_app().db

        income, expense, balance = db.totals()

        text = (
            f"💵 Total Income\n"
            f"₹ {income:,.2f}\n\n"
            f"💸 Total Expenses\n"
            f"₹ {expense:,.2f}\n\n"
            f"💰 Current Balance\n"
            f"₹ {balance:,.2f}\n\n"
            f"🏷️ Expense Categories\n\n"
        )

        categories = db.category_totals()

        if categories:
            for category, amount in categories:
                text += f"{category}: ₹ {amount:,.2f}\n"
        else:
            text += "No expenses yet."

        self.report.text = text

    def go(self, screen):
        self.manager.current = screen


# ---------------- BUDGET ----------------

class Budget(Screen):

    def on_pre_enter(self):
        self.refresh()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(8)
        )

        self.add_widget(layout)

        layout.add_widget(title("🎯 Budgets"))

        self.category = Spinner(
            text="Food",
            values=(
                "Food",
                "Travel",
                "Shopping",
                "Bills",
                "Education",
                "Health",
                "Entertainment",
                "Other"
            ),
            size_hint_y=None,
            height=dp(50)
        )

        self.amount = TextInput(
            hint_text="Budget amount ₹",
            input_filter="float",
            multiline=False,
            size_hint_y=None,
            height=dp(50)
        )

        layout.add_widget(self.category)
        layout.add_widget(self.amount)

        save = make_button("💾 Set Budget")
        save.bind(on_release=self.save)
        layout.add_widget(save)

        self.list_label = Label(
            text="",
            font_size=dp(16)
        )

        layout.add_widget(self.list_label)

        back = make_button("⬅ Dashboard")
        back.bind(
            on_release=lambda x:
            self.go("dashboard")
        )

        layout.add_widget(back)

    def save(self, instance):

        try:
            amount = float(self.amount.text)

            if amount <= 0:
                raise ValueError

            App.get_running_app().db.set_budget(
                self.category.text,
                amount
            )

            self.amount.text = ""
            self.refresh()

        except ValueError:
            Popup(
                title="MoneyFlow",
                content=Label(
                    text="Enter a valid budget."
                ),
                size_hint=(0.8, 0.3)
            ).open()

    def refresh(self):

        budgets = App.get_running_app().db.get_budgets()

        text = "Current Budgets\n\n"

        if not budgets:
            text += "No budgets set."

        for category, amount in budgets:
            text += f"🎯 {category}: ₹ {amount:,.2f}\n"

        self.list_label.text = text

    def go(self, screen):
        self.manager.current = screen


# ---------------- SETTINGS ----------------

class Settings(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        self.add_widget(layout)

        layout.add_widget(
            title("⚙️ Settings")
        )

        export = make_button("📤 Export CSV")

        export.bind(
            on_release=self.export_data
        )

        layout.add_widget(export)

        info = Label(
            text=(
                "MoneyFlow Ultra Pro Max\n\n"
                "Your transaction data is stored "
                "locally on this device.\n\n"
                "Version 1.0"
            ),
            font_size=dp(17)
        )

        layout.add_widget(info)

        back = make_button("⬅ Dashboard")

        back.bind(
            on_release=lambda x:
            self.go("dashboard")
        )

        layout.add_widget(back)

    def export_data(self, instance):

        path = os.path.join(
            os.path.expanduser("~"),
            "MoneyFlow_Transactions.csv"
        )

        try:
            App.get_running_app().db.export_csv(path)

            Popup(
                title="Export Complete",
                content=Label(
                    text=f"Saved to:\n{path}"
                ),
                size_hint=(0.85, 0.4)
            ).open()

        except Exception as e:

            Popup(
                title="Export Error",
                content=Label(text=str(e)),
                size_hint=(0.85, 0.4)
            ).open()

    def go(self, screen):
        self.manager.current = screen


# ---------------- APP ----------------

class MoneyFlowApp(App):

    def build(self):

        self.title = APP_NAME

        self.db = Database()

        manager = ScreenManager()

        manager.add_widget(
            Dashboard(name="dashboard")
        )

        manager.add_widget(
            AddTransaction(name="add")
        )

        manager.add_widget(
            History(name="history")
        )

        manager.add_widget(
            Reports(name="reports")
        )

        manager.add_widget(
            Budget(name="budget")
        )

        manager.add_widget(
            Settings(name="settings")
        )

        return manager


if __name__ == "__main__":
    MoneyFlowApp().run()
