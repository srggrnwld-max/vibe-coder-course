import base64
import getpass
import hashlib
import secrets
import sqlite3
import string
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class DatabaseManager:
    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or Path(__file__).with_name("passwords.db")
        self._create_tables()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS passwords (
                    service TEXT PRIMARY KEY COLLATE NOCASE,
                    login TEXT NOT NULL,
                    encrypted_password TEXT NOT NULL
                )
                """
            )

    def get_setting(self, name: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE name = ?", (name,)
            ).fetchone()
            return str(row["value"]) if row else None

    def set_setting(self, name: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)",
                (name, value),
            )

    def save_password(self, service: str, login: str, encrypted_password: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO passwords (service, login, encrypted_password)
                VALUES (?, ?, ?)
                """,
                (service, login, encrypted_password),
            )

    def get_password(self, service: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM passwords WHERE service = ?", (service,)
            ).fetchone()

    def list_passwords(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(connection.execute("SELECT service, login FROM passwords ORDER BY service"))

    def delete_password(self, service: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM passwords WHERE service = ?", (service,))
            return cursor.rowcount > 0


class EncryptionManager:
    def __init__(self, key_path: Path | None = None) -> None:
        self.key_path = key_path or Path(__file__).with_name("vault.key")
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        return self.fernet.decrypt(value.encode("ascii")).decode("utf-8")


class MasterPassword:
    ITERATIONS = 600_000

    @classmethod
    def create_hash(cls, password: str, salt: bytes | None = None) -> tuple[str, str]:
        actual_salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), actual_salt, cls.ITERATIONS
        )
        return base64.b64encode(actual_salt).decode("ascii"), base64.b64encode(digest).decode("ascii")

    @classmethod
    def verify(cls, password: str, salt_text: str, digest_text: str) -> bool:
        salt = base64.b64decode(salt_text)
        _, candidate = cls.create_hash(password, salt)
        return secrets.compare_digest(candidate, digest_text)


class PasswordGenerator:
    SIMILAR_CHARACTERS = set("0O1lI")

    @classmethod
    def generate(cls, length: int = 16, exclude_similar: bool = True) -> str:
        if length < 8 or length > 64:
            raise ValueError("Длина должна быть от 8 до 64 символов")
        groups = [string.ascii_lowercase, string.ascii_uppercase, string.digits, "!@#$%^&*()-_=+"]
        if exclude_similar:
            groups = ["".join(char for char in group if char not in cls.SIMILAR_CHARACTERS) for group in groups]

        characters = "".join(groups)
        while True:
            password = "".join(secrets.choice(characters) for _ in range(length))
            if all(any(char in group for char in password) for group in groups):
                return password


class PasswordManagerApp:
    def __init__(self) -> None:
        self.database = DatabaseManager()
        self.encryption = EncryptionManager()

    def setup_or_authenticate(self) -> bool:
        stored_hash = self.database.get_setting("master_hash")
        stored_salt = self.database.get_setting("master_salt")
        if not stored_hash or not stored_salt:
            print("Первый запуск. Создайте мастер-пароль.")
            password = getpass.getpass("Новый мастер-пароль: ")
            confirmation = getpass.getpass("Повторите мастер-пароль: ")
            if password != confirmation or len(password) < 8:
                print("Пароли не совпадают или короче 8 символов.")
                return False
            salt, digest = MasterPassword.create_hash(password)
            self.database.set_setting("master_salt", salt)
            self.database.set_setting("master_hash", digest)
            print("Мастер-пароль установлен.")
            return True

        password = getpass.getpass("Мастер-пароль: ")
        if not MasterPassword.verify(password, stored_salt, stored_hash):
            print("Неверный мастер-пароль.")
            return False
        return True

    def add_password(self) -> None:
        service = input("Название сервиса: ").strip()
        login = input("Логин: ").strip()
        if not service or not login:
            print("Название и логин обязательны.")
            return
        choice = input("Сгенерировать пароль? [Д/н]: ").strip().lower()
        if choice in {"", "д", "да", "y", "yes"}:
            password = self.generate_password_interactive()
        else:
            password = getpass.getpass("Пароль: ")
        self.database.save_password(service, login, self.encryption.encrypt(password))
        print(f"Запись «{service}» сохранена. Пароль: {password}")

    def generate_password_interactive(self) -> str:
        length_text = input("Длина [16]: ").strip()
        length = int(length_text) if length_text else 16
        exclude = input("Исключить похожие 0/O, 1/l/I? [Д/н]: ").strip().lower()
        password = PasswordGenerator.generate(length, exclude not in {"н", "нет", "n", "no"})
        print(f"Новый пароль: {password}")
        return password

    def show_password(self) -> None:
        service = input("Название сервиса: ").strip()
        row = self.database.get_password(service)
        if not row:
            print("Запись не найдена.")
            return
        try:
            password = self.encryption.decrypt(row["encrypted_password"])
        except InvalidToken:
            print("Не удалось расшифровать пароль: ключ не подходит.")
            return
        print(f"Сервис: {row['service']}")
        print(f"Логин: {row['login']}")
        print(f"Пароль: {password}")

    def list_passwords(self) -> None:
        rows = self.database.list_passwords()
        if not rows:
            print("Сохранённых записей пока нет.")
            return
        for row in rows:
            print(f"- {row['service']}: {row['login']}")

    def delete_password(self) -> None:
        service = input("Название сервиса: ").strip()
        print("Запись удалена." if self.database.delete_password(service) else "Запись не найдена.")

    def run(self) -> None:
        if not self.setup_or_authenticate():
            return
        actions = {
            "1": self.add_password,
            "2": self.show_password,
            "3": self.list_passwords,
            "4": self.delete_password,
            "5": self.generate_password_interactive,
        }
        while True:
            print("\n1 — добавить | 2 — получить | 3 — список | 4 — удалить | 5 — генератор | 0 — выход")
            choice = input("Выберите действие: ").strip()
            if choice == "0":
                print("До свидания!")
                break
            action = actions.get(choice)
            if action:
                try:
                    action()
                except ValueError as error:
                    print(f"Ошибка: {error}")
            else:
                print("Неизвестная команда.")


if __name__ == "__main__":
    PasswordManagerApp().run()
