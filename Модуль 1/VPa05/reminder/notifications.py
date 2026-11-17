import tkinter as tk
from tkinter import messagebox

from database import ReminderDatabase


class NotificationManager:
    def __init__(self, root: tk.Tk, database: ReminderDatabase) -> None:
        self.root = root
        self.database = database
        self.on_change = lambda: None

    def start(self) -> None:
        self._check_reminders()

    def _check_reminders(self) -> None:
        for reminder in self.database.get_due_reminders():
            self._show_popup(reminder["title"], reminder["description"])
            self.database.complete_due_reminder(reminder)
        self.on_change()
        self.root.after(10_000, self._check_reminders)

    def _show_popup(self, title: str, description: str) -> None:
        messagebox.showinfo(f"Напоминание: {title}", description or title, parent=self.root)

    def test_notification(self) -> None:
        self._show_popup("Проверка", "Уведомления работают")
