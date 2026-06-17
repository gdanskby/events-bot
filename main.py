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


def is_tomorrow(date_str):
    try:
        event_date = datetime.fromisoformat(date_str[:10])
        tomorrow = datetime.now().date() + timedelta(days=1)
        return event_date.date() == tomorrow
    except:
        return False


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

            # ❗ ФИЛЬТР ЗАВТРА
            if not start or not is_tomorrow(start):
                return None

            title = data.get("name")
            image = data.get("image")

            loc = data.get("location", {})
            address = ""

            if isinstance(loc, dict):
                addr = loc.get("address", {})
                if isinstance(addr, dict):
                    street = addr.get("streetAddress", "")
                    city = addr.get("addressLocality", "")
                    address = f"{street}, {city}".strip(", ")

            time = start[11:16] if "T" in start else ""

            return {
                "title": title,
                "image": image,
                "time": time,
                "date": start[:10],
                "address": address or "Trójmiasto",
                "url": url
            }

        except:
            continue

    return None


def send():
    sent = 0

    for url in get_links():
        e = parse_event(url)

        if not e:
            continue

        text = f"""🎉 {e['title']}

⌛ {e['time']}
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
