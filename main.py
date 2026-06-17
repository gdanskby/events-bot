import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

BASE = "https://www.trojmiasto.pl"
START = "https://www.trojmiasto.pl/imprezy/wstepwolny,1.html"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_links():
    r = requests.get(START, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # 🔥 ТОЛЬКО реальные события (есть запятая в URL)
        if "/imprezy/" in href and "," in href:
            full = href if href.startswith("http") else BASE + href
            links.add(full)

    return list(links)[:8]


def parse(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("h1")
    title = title.get_text(strip=True) if title else None

    # 🖼 самая стабильная картинка
    img = soup.find("meta", property="og:image")
    img = img["content"] if img else None

    # 📍 адрес через карту
    address = None
    for a in soup.find_all("a", href=True):
        if "map" in a["href"] or "google" in a["href"]:
            address = a.get_text(strip=True)
            break

    # ⏰ время (очень грубо, но работает часто)
    time = None
    for t in soup.find_all(text=True):
        if ":" in t and any(x in t for x in ["18", "19", "20"]):
            time = t.strip()
            break

    return {
        "title": title,
        "img": img,
        "address": address or "Trójmiasto",
        "time": time or "",
        "url": url
    }


def send():
    for url in get_links():
        e = parse(url)

        if not e["title"]:
            continue

        text = f"""🎉 {e['title']}

⌛ {e['time']}
📍 {e['address']}

🔗 {e['url']}"""

        try:
            if e["img"]:
                bot.send_photo(CHAT_ID, photo=e["img"], caption=text)
            else:
                bot.send_message(CHAT_ID, text)
        except:
            bot.send_message(CHAT_ID, text)


if __name__ == "__main__":
    send()
    
