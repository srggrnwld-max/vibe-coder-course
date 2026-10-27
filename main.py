import requests

url = "https://example.com"
response = requests.get(url, timeout=10)

print(f"Статус-код: {response.status_code}")
print(f"Адрес запроса: {response.url}")
