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
def tomorrow_str():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def is_tomorrow(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date() == (
            datetime.now().date() + timedelta(days=1)
        )
    except:
        return False


# -----------------------
# ВЫТАСКИВАЕМ ДАТУ ИЗ ТЕКСТА
# -----------------------
def extract_date(text):
    if not text:
        return None

    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)

    return None


# -----------------------
# БЕСПЛАТНЫЕ
# -----------------------
def is_free_event(text, url):
    text = (text or "").lower()
    url = (url or "").lower()

    return (
        "wstęp wolny" in text
        or "wstep wolny" in text
        or "bezpłatny" in text
        or "bezplatny" in text
        or "wstepwolny" in url
    )


# -----------------------
# КРАСИВАЯ ДАТА
# -----------------------
def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")

        days = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
        months = ["","января","февраля","марта","апреля","мая","июня",
                  "июля","августа","сентября","октября","ноября","декабря"]

        return f"{dt.day} {months[dt.month]} ({days[dt.weekday()]})"
    except:
        return ""


# -----------------------
# ССЫЛКА НА ДЕНЬ
# -----------------------
def build_url():
    d = tomorrow_str()
    return f"https://m.trojmiasto.pl/imprezy/dzien,{d},wstepwolny,1_5,o0,1.html"


# -----------------------
# ССЫЛКИ СОБЫТИЙ
# -----------------------
def get_links(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "imprezy" in href and "," in href:
            full = href if href.startswith("http") else "https://www.trojmiasto.pl" + href
            links.add(full)

    return list(links)


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

            raw = json.dumps(data, ensure_ascii=False)

            # ❗ бесплатное
            if not is_free_event(raw, url):
                return None

            title = data.get("name")
            image = data.get("image")

            # дата
            start = data.get("startDate") or raw
            date_only = extract_date(start)

            if not date_only:
                return None

            # ❗ только завтра
            if not is_tomorrow(date_only):
                return None

            # время
            time = ""
            try:
                time = data.get("startDate", "").split("T")[1][:5]
            except:
                pass

            # адрес
            address = "Trójmiasto"
            loc = data.get("location", {})

            if isinstance(loc, dict):
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    street = addr.get("streetAddress", "")
                    city = addr.get("addressLocality", "")
                    address = f"{street}, {city}".strip(", ")

            return {
                "title": title,
                "image": image,
                "time": time,
                "date": date_only,
                "address": address,
                "url": url
            }

        except:
            continue

    return None


# -----------------------
# ОТПРАВКА АФИШИ
# -----------------------
def send():
    url = build_url()
    links = get_links(url)

    events = []
    seen = set()

    for link in links:
        if link in seen:
            continue
        seen.add(link)

        e = parse_event(link)
        if not e:
            continue

        events.append(e)

    if not events:
        bot.send_message(CHAT_ID, "На завтра бесплатных мероприятий не найдено")
        return

    text = f"🎉 Бесплатные мероприятия на {format_date(tomorrow_str())}\n\n"

    for i, e in enumerate(events[:10], 1):
        text += f"""{i}) 🎉 {e['title']}
⌛ {e['time']}
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
