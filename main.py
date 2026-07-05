import os
import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

HEADERS = {"User-Agent": "Mozilla/5.0"}


# -----------------------
# ЗАВТРА
# -----------------------
def tomorrow():
    return (datetime.now() + timedelta(days=1)).date()


def tomorrow_str():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


# -----------------------
# ПЕРЕВОД НАЗВАНИЯ
# -----------------------
def translate(text):
    if not text:
        return ""

    rules = {
        "Koncert": "Концерт",
        "koncert": "концерт",
        "Festiwal": "Фестиваль",
        "festiwal": "фестиваль",
        "Wystawa": "Выставка",
        "wystawa": "выставка",
        "Spektakl": "Спектакль",
        "Teatr": "Театр",
        "dla dzieci": "для детей",
        "Impreza": "Мероприятие",
    }

    for k, v in rules.items():
        text = text.replace(k, v)

    return text


# -----------------------
# ИСТОЧНИКИ
# -----------------------
def sources():
    d = tomorrow_str()

    return [
        f"https://m.trojmiasto.pl/imprezy/dzien,{d},wstepwolny,1_5,o0,1.html",
        "https://m.trojmiasto.pl/imprezy/wstepwolny,1_5,o0,1.html"
    ]


# -----------------------
# ССЫЛКИ
# -----------------------
def get_links(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]

            if "imprezy" in href:
                full = href if href.startswith("http") else "https://m.trojmiasto.pl" + href
                links.add(full)

        return list(links)
    except:
        return []


# -----------------------
# БЕСПЛАТНЫЕ
# -----------------------
def is_free(text):
    t = (text or "").lower()
    return "wstęp wolny" in t or "wstep wolny" in t


# -----------------------
# ДАТА ИЗ ТЕКСТА
# -----------------------
def extract_date(text):
    if not text:
        return None

    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        return datetime.strptime(m.group(0), "%Y-%m-%d").date()

    return None


# -----------------------
# ПАРСИНГ
# -----------------------
def parse(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        text_all = soup.get_text(" ", strip=True)

        # ❗ фильтр бесплатных
        if not is_free(text_all):
            return None

        title = None
        image = None
        date = None
        address = "Trójmiasto"

        scripts = soup.find_all("script", type="application/ld+json")

        for s in scripts:
            try:
                data = json.loads(s.string)

                if isinstance(data, list):
                    data = data[0]

                if isinstance(data, dict) and data.get("@type") == "Event":
                    title = data.get("name")
                    image = data.get("image")

                    start = data.get("startDate")
                    if start:
                        date = extract_date(start)

                    loc = data.get("location", {})
                    if isinstance(loc, dict):
                        addr = loc.get("address", {})
                        if isinstance(addr, dict):
                            street = addr.get("streetAddress", "")
                            city = addr.get("addressLocality", "")
                            address = f"{street}, {city}".strip(", ")

            except:
                continue

        if not title or not date:
            return None

        # ❗ только завтра
        if date != tomorrow():
            return None

        return {
            "title": translate(title),
            "image": image,
            "address": address,
            "url": url
        }

    except:
        return None


# -----------------------
# ОТПРАВКА
# -----------------------
def send():
    all_links = set()

    for s in sources():
        all_links.update(get_links(s))

    events = []
    seen = set()

    for link in all_links:
        if link in seen:
            continue
        seen.add(link)

        e = parse(link)
        if e:
            events.append(e)

    if not events:
        bot.send_message(CHAT_ID, "На завтра бесплатных мероприятий не найдено")
        return

    text = "🎉 Бесплатные мероприятия на завтра\n\n"

    for i, e in enumerate(events[:10], 1):
        text += f"""{i}) 🎉 {e['title']}
📍 {e['address']}
🔗 {e['url']}

"""

    try:
        if events[0]["image"]:
            bot.send_photo(CHAT_ID, photo=events[0]["image"], caption=text)
        else:
            bot.send_message(CHAT_ID, text)
    except:
        bot.send_message(CHAT_ID, text)


if __name__ == "__main__":
    send()
