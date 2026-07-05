import os
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

HEADERS = {"User-Agent": "Mozilla/5.0"}


# -----------------------
# ЗАВТРАШНЯЯ ДАТА
# -----------------------
def get_tomorrow():
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


# -----------------------
# ССЫЛКА НА ДЕНЬ + FREE
# -----------------------
def build_url():
    date = get_tomorrow()
    return f"https://m.trojmiasto.pl/imprezy/dzien,{date},wstepwolny,1_5,o0,1.html"


# -----------------------
# ПОЛУЧАЕМ ССЫЛКИ СОБЫТИЙ
# -----------------------
def get_event_links(url):
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
# ПАРСИНГ СОБЫТИЯ (JSON-LD)
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

            title = data.get("name")
            image = data.get("image")
            start = data.get("startDate")

            if not title or not start:
                continue

            # время
            time = ""
            try:
                time = start.split("T")[1][:5]
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
                "address": address,
                "url": url
            }

        except:
            continue

    return None


# -----------------------
# ОТПРАВКА ОДНОЙ АФИШИ
# -----------------------
def send():
    url = build_url()
    links = get_event_links(url)

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

    # -------- афиша --------
    text = f"🎉 Бесплатные мероприятия на {get_tomorrow()}\n\n"

    for i, e in enumerate(events[:10], 1):
        text += f"""{i}) 🎉 {e['title']}
⌛ {e['time']}
📍 {e['address']}
🔗 {e['url']}

"""

    # отправляем фото первого события (если есть)
    try:
        first = events[0]
        if first["image"]:
            bot.send_photo(CHAT_ID, photo=first["image"], caption=text)
        else:
            bot.send_message(CHAT_ID, text)
    except:
        bot.send_message(CHAT_ID, text)


if __name__ == "__main__":
    send()
