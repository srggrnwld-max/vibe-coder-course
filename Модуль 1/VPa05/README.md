# VPa05 — Создаём напоминалку и генератор паролей

Практическая работа состоит из двух приложений:

- `reminder` — desktop-напоминалка на Tkinter с локальной базой SQLite;
- `password-manager` — учебный CLI-менеджер с генерацией и шифрованием тестовых паролей.

## Запуск напоминалки

```powershell
.\venv\Scripts\python.exe ".\Модуль 1\VPa05\reminder\main.py"
```

## Запуск менеджера паролей

Сначала установите зависимость в виртуальное окружение:

```powershell
.\venv\Scripts\python.exe -m pip install -r ".\Модуль 1\VPa05\password-manager\requirements.txt"
```

Затем запустите программу:

```powershell
.\venv\Scripts\python.exe ".\Модуль 1\VPa05\password-manager\password_manager.py"
```

Менеджер предназначен только для учебных записей. Не используйте в нём настоящие пароли.
