import os
import requests
import json
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

URL = "https://www.trojmiasto.pl/imprezy/wstepwolny,1.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_event_pages():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # берём только реальные страницы событий
        if "imp" in href and "imprezy" in href:
            full = href if href.startswith("http") else "https://www.trojmiasto.pl" + href
            links.add(full)

    return list(links)[:10]


def extract_event_data(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    scripts = soup.find_all("script", type="application/ld+json")

    for s in scripts:
        try:
            data = json.loads(s.string)

            # иногда список
            if isinstance(data, list):
                data = data[0]

            if data.get("@type") != "Event":
                continue

            title = data.get("name")
            image = data.get("image")
            start = data.get("startDate")

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


def send():
    for url in get_event_pages():
        e = extract_event_data(url)

        if not e or not e["title"]:
            continue

        text = f"""🎉 {e['title']}

📅 {e['date']}
📍 {e['address']}

🔗 {e['url']}"""

        try:
            if e["image"]:
                bot.send_photo(CHAT_ID, photo=e["image"], caption=text)
            else:
                bot.send_message(CHAT_ID, text)
        except:
            bot.send_message(CHAT_ID, text)


if __name__ == "__main__":
    send()
