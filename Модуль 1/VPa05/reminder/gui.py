import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from database import ReminderDatabase
from notifications import NotificationManager


class ReminderApp:
    DATE_FORMAT = "%d.%m.%Y %H:%M"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.database = ReminderDatabase()
        self.notifications = NotificationManager(root, self.database)
        self.notifications.on_change = self.refresh_reminders
        self._setup_ui()
        self.refresh_reminders()
        self.notifications.start()

    def _setup_ui(self) -> None:
        self.root.title("VPa05 — Напоминалка")
        self.root.geometry("900x560")
        self.root.minsize(760, 480)

        form = ttk.LabelFrame(self.root, text="Новое напоминание", padding=12)
        form.pack(fill="x", padx=12, pady=12)

        ttk.Label(form, text="Название").grid(row=0, column=0, sticky="w")
        self.title_entry = ttk.Entry(form, width=32)
        self.title_entry.grid(row=1, column=0, padx=(0, 8), sticky="ew")

        ttk.Label(form, text="Описание").grid(row=0, column=1, sticky="w")
        self.description_entry = ttk.Entry(form, width=42)
        self.description_entry.grid(row=1, column=1, padx=(0, 8), sticky="ew")

        ttk.Label(form, text="Дата и время").grid(row=0, column=2, sticky="w")
        self.due_entry = ttk.Entry(form, width=18)
        self.due_entry.insert(0, (datetime.now() + timedelta(minutes=5)).strftime(self.DATE_FORMAT))
        self.due_entry.grid(row=1, column=2, padx=(0, 8), sticky="ew")

        ttk.Label(form, text="Повтор").grid(row=0, column=3, sticky="w")
        self.repeat_box = ttk.Combobox(
            form, values=("Нет", "Ежедневно", "Еженедельно"), state="readonly", width=14
        )
        self.repeat_box.set("Нет")
        self.repeat_box.grid(row=1, column=3, sticky="ew")

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=4, pady=(10, 0), sticky="w")
        ttk.Button(buttons, text="Добавить", command=self.add_reminder).pack(side="left")
        ttk.Button(buttons, text="Через 1 минуту", command=lambda: self.set_quick_time(1)).pack(side="left", padx=5)
        ttk.Button(buttons, text="Через 5 минут", command=lambda: self.set_quick_time(5)).pack(side="left")
        ttk.Button(buttons, text="Через 30 минут", command=lambda: self.set_quick_time(30)).pack(side="left", padx=5)
        ttk.Button(buttons, text="Тест уведомления", command=self.notifications.test_notification).pack(side="left")

        for column in range(4):
            form.columnconfigure(column, weight=1)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=12)
        ttk.Label(toolbar, text="Фильтр:").pack(side="left")
        self.filter_box = ttk.Combobox(
            toolbar,
            values=("Все", "Ожидает", "Готово", "Просрочено", "Отменено"),
            state="readonly",
            width=15,
        )
        self.filter_box.set("Все")
        self.filter_box.pack(side="left", padx=6)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_reminders())

        columns = ("id", "title", "due_at", "repeat_rule", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=14)
        headings = {
            "id": "ID",
            "title": "Название",
            "due_at": "Дата и время",
            "repeat_rule": "Повтор",
            "status": "Статус",
        }
        widths = {"id": 55, "title": 310, "due_at": 160, "repeat_rule": 120, "status": 110}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center" if column != "title" else "w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=10)

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(actions, text="Готово", command=lambda: self.change_status("Готово")).pack(side="left")
        ttk.Button(actions, text="Отменить", command=lambda: self.change_status("Отменено")).pack(side="left", padx=5)
        ttk.Button(actions, text="Удалить", command=self.delete_reminder).pack(side="left")
        self.status_label = ttk.Label(actions, text="")
        self.status_label.pack(side="right")

    def set_quick_time(self, minutes: int) -> None:
        self.due_entry.delete(0, tk.END)
        self.due_entry.insert(0, (datetime.now() + timedelta(minutes=minutes)).strftime(self.DATE_FORMAT))

    def add_reminder(self) -> None:
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Не заполнено", "Введите название напоминания", parent=self.root)
            return
        try:
            due_at = datetime.strptime(self.due_entry.get().strip(), self.DATE_FORMAT)
        except ValueError:
            messagebox.showerror("Ошибка", "Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ", parent=self.root)
            return
        self.database.add_reminder(
            title, self.description_entry.get().strip(), due_at, self.repeat_box.get()
        )
        self.title_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.refresh_reminders()

    def _selected_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Не выбрано", "Выберите напоминание", parent=self.root)
            return None
        return int(self.tree.item(selection[0], "values")[0])

    def change_status(self, status: str) -> None:
        reminder_id = self._selected_id()
        if reminder_id is not None:
            self.database.update_status(reminder_id, status)
            self.refresh_reminders()

    def delete_reminder(self) -> None:
        reminder_id = self._selected_id()
        if reminder_id is not None and messagebox.askyesno(
            "Удаление", "Удалить выбранное напоминание?", parent=self.root
        ):
            self.database.delete_reminder(reminder_id)
            self.refresh_reminders()

    def refresh_reminders(self) -> None:
        self.database.mark_overdue()
        for item in self.tree.get_children():
            self.tree.delete(item)
        reminders = self.database.get_reminders(self.filter_box.get())
        for reminder in reminders:
            due_at = datetime.fromisoformat(reminder["due_at"]).strftime(self.DATE_FORMAT)
            self.tree.insert(
                "",
                "end",
                values=(
                    reminder["id"],
                    reminder["title"],
                    due_at,
                    reminder["repeat_rule"],
                    reminder["status"],
                ),
            )
        self.status_label.config(text=f"Записей: {len(reminders)}")
