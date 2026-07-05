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
# ДАТА
# -----------------------
def tomorrow_date():
    return (datetime.now() + timedelta(days=1)).date()


def tomorrow_str():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


# -----------------------
# ПЕРЕВОД (оставляем, он норм)
# -----------------------
def translate(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "pl",
            "tl": "ru",
            "dt": "t",
            "q": text
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return "".join([x[0] for x in data[0]])
    except:
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
# ДАТА
# -----------------------
def extract_date(text):
    if not text:
        return None

    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        return datetime.strptime(m.group(0), "%Y-%m-%d").date()

    return None


# -----------------------
# ПАРСИНГ (УПРОЩЁННЫЙ = СТАБИЛЬНЫЙ)
# -----------------------
def parse(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")

        text_all = soup.get_text(" ", strip=True)

        # ❗ только бесплатные
        if not is_free(text_all):
            return None

        title = soup.find("h1")
        title = title.text.strip() if title else None

        if not title:
            return None

        # ищем дату в JSON-LD
        date = None

        scripts = soup.find_all("script", type="application/ld+json")

        for s in scripts:
            try:
                data = json.loads(s.string)

                if isinstance(data, list):
                    data = data[0]

                if isinstance(data, dict):
                    start = data.get("startDate")
                    if start:
                        date = extract_date(start)

            except:
                continue

        if not date:
            # fallback — ищем в тексте страницы
            date = extract_date(text_all)

        if not date:
            return None

        # ❗ только завтра
        if date != tomorrow_date():
            return None

        # адрес (просто текстом)
        address = "Trójmiasto"

        loc = soup.get_text(" ", strip=True)
        if "Sopot" in loc:
            address = "Sopot"
        elif "Gdańsk" in loc:
            address = "Gdańsk"
        elif "Gdynia" in loc:
            address = "Gdynia"

        return {
            "title": translate(title),
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

    for i, e in enumerate(events[:15], 1):
        text += f"""{i}) 🎉 {e['title']}
📍 {e['address']}
🔗 {e['url']}

"""

    bot.send_message(CHAT_ID, text)


if __name__ == "__main__":
    send()
