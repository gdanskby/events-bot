import os
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

URL = "https://www.trojmiasto.pl/imprezy/wstepwolny,1.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}


# -----------------------
# ФИЛЬТР БЕСПЛАТНЫХ
# -----------------------
def is_free_event(text, url):
    text = (text or "").lower()
    url = (url or "").lower()

    keywords = [
        "wstęp wolny",
        "wstep wolny",
        "bezpłatny",
        "bezplatny",
        "free"
    ]

    if any(k in text for k in keywords):
        return True

    if "wstepwolny" in url:
        return True

    return False


# -----------------------
# ТОЛЬКО ЗАВТРА
# -----------------------
def is_tomorrow(date_str):
    try:
        dt = datetime.fromisoformat(date_str[:10])
        tomorrow = datetime.now().date() + timedelta(days=1)
        return dt.date() == tomorrow
    except:
        return False


# -----------------------
# ДАТА В ТЕКСТ
# -----------------------
def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str[:10])

        days = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
        months = ["","января","февраля","марта","апреля","мая","июня",
                  "июля","августа","сентября","октября","ноября","декабря"]

        return f"{dt.day} {months[dt.month]} ({days[dt.weekday()]})"
    except:
        return ""


# -----------------------
# ПЕРЕВОД НАЗВАНИЯ (простое)
# -----------------------
def translate_title(text):
    if not text:
        return ""

    replacements = {
        "Koncert": "Концерт",
        "koncert": "концерт",
        "Wystawa": "Выставка",
        "wystawa": "выставка",
        "Festiwal": "Фестиваль",
        "festiwal": "фестиваль",
        "Dla dzieci": "Для детей",
        "Impreza": "Мероприятие",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


# -----------------------
# ПОЛУЧЕНИЕ ССЫЛОК
# -----------------------
def get_links():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/imprezy/" in href and "," in href:
            full = href if href.startswith("http") else "https://www.trojmiasto.pl" + href
            links.add(full)

    return list(links)[:15]


# -----------------------
# ПАРСИНГ СОБЫТИЯ
# -----------------------
def parse_event(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    scripts = soup.find_all("script", type="application/ld+json")

    for s in scripts:
        try:
            data = json.loads(s.string)

            if isinstance(data, list):
                data = data[0]

            if data.get("@type") != "Event":
                continue

            start = data.get("startDate")
            if not start:
                continue

            # ❗ только завтра
            if not is_tomorrow(start):
                return None

            # ❗ фильтр бесплатных
            raw_text = json.dumps(data, ensure_ascii=False)

            if not is_free_event(raw_text, url):
                return None

            title = translate_title(data.get("name"))
            image = data.get("image")

            loc = data.get("location", {})
            address = ""

            if isinstance(loc, dict):
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    street = addr.get("streetAddress", "")
                    city = addr.get("addressLocality", "")
                    address = f"{street}, {city}".strip(", ")

            return {
                "title": title,
                "image": image,
                "date": start,
                "address": address or "Trójmiasto",
                "url": url
            }

        except:
            continue

    return None


# -----------------------
# ОТПРАВКА
# -----------------------
def send():
    sent = 0

    for url in get_links():
        e = parse_event(url)

        if not e:
            continue

        date_text = format_date(e["date"])

        text = f"""🎉 {e['title']}

📅 {date_text}
📍 {e['address']}

🔗 {e['url']}"""

        try:
            if e["image"]:
                bot.send_photo(CHAT_ID, photo=e["image"], caption=text)
            else:
                bot.send_message(CHAT_ID, text)
        except:
            bot.send_message(CHAT_ID, text)

        sent += 1

    if sent == 0:
        bot.send_message(CHAT_ID, "Завтра бесплатных мероприятий не найдено")


if __name__ == "__main__":
    send()
