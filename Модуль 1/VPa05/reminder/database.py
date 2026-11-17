import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class ReminderDatabase:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or Path(__file__).with_name("reminders.db")
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    due_at TEXT NOT NULL,
                    repeat_rule TEXT NOT NULL DEFAULT 'Нет',
                    status TEXT NOT NULL DEFAULT 'Ожидает',
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_reminder(
        self, title: str, description: str, due_at: datetime, repeat_rule: str
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders
                    (title, description, due_at, repeat_rule, status, created_at)
                VALUES (?, ?, ?, ?, 'Ожидает', ?)
                """,
                (
                    title,
                    description,
                    due_at.isoformat(timespec="minutes"),
                    repeat_rule,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return int(cursor.lastrowid)

    def get_reminders(self, status: str = "Все") -> list[sqlite3.Row]:
        query = "SELECT * FROM reminders"
        parameters: tuple[str, ...] = ()
        if status != "Все":
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY due_at"
        with self._connect() as connection:
            return list(connection.execute(query, parameters))

    def get_due_reminders(self, now: datetime | None = None) -> list[sqlite3.Row]:
        current_time = (now or datetime.now()).isoformat(timespec="minutes")
        with self._connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM reminders
                    WHERE status = 'Ожидает' AND due_at <= ?
                    ORDER BY due_at
                    """,
                    (current_time,),
                )
            )

    def complete_due_reminder(self, reminder: sqlite3.Row) -> None:
        repeat_rule = reminder["repeat_rule"]
        if repeat_rule in {"Ежедневно", "Еженедельно"}:
            due_at = datetime.fromisoformat(reminder["due_at"])
            step = timedelta(days=1 if repeat_rule == "Ежедневно" else 7)
            while due_at <= datetime.now():
                due_at += step
            with self._connect() as connection:
                connection.execute(
                    "UPDATE reminders SET due_at = ? WHERE id = ?",
                    (due_at.isoformat(timespec="minutes"), reminder["id"]),
                )
        else:
            self.update_status(reminder["id"], "Готово")

    def update_status(self, reminder_id: int, status: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE reminders SET status = ? WHERE id = ?",
                (status, reminder_id),
            )

    def mark_overdue(self, now: datetime | None = None) -> None:
        overdue_before = ((now or datetime.now()) - timedelta(minutes=1)).isoformat(
            timespec="minutes"
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE reminders
                SET status = 'Просрочено'
                WHERE status = 'Ожидает'
                  AND repeat_rule = 'Нет'
                  AND due_at < ?
                """,
                (overdue_before,),
            )

    def delete_reminder(self, reminder_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
