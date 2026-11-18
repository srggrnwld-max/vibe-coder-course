"""Учебный PDF-чек-мейкер: CSV → HTML-шаблон → отдельный PDF на заказ."""

import csv
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "orders.csv"
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"


def read_orders(path):
    """Читает строки CSV и собирает их в заказы по order_id."""
    orders = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            order = orders.setdefault(
                row["order_id"],
                {
                    "order_id": row["order_id"],
                    "date": row["date"],
                    "customer": row["customer"],
                    "items": [],
                },
            )
            quantity = int(row["quantity"])
            price = float(row["price"])
            order["items"].append(
                {
                    "item": row["item"],
                    "quantity": quantity,
                    "price": price,
                    "line_total": quantity * price,
                }
            )

    for order in orders.values():
        order["total"] = sum(item["line_total"] for item in order["items"])
    return list(orders.values())


def render_check(env, order):
    """Подставляет данные заказа в HTML-шаблон чека."""
    template = env.get_template("check.html")
    return template.render(order=order)


def save_pdf(html, path):
    """Сохраняет готовый HTML как PDF."""
    HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf(path)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    for order in read_orders(DATA_FILE):
        pdf_path = OUTPUT_DIR / f"check-{order['order_id']}.pdf"
        save_pdf(render_check(env, order), pdf_path)
        print(pdf_path.name)


if __name__ == "__main__":
    main()
