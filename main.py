import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

URL = "https://www.trojmiasto.pl/imprezy/wstepwolny,1_5.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_events():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    events = []

    # ищем ссылки на события (самый стабильный способ для этого сайта)
    cards = soup.select("a[href*='/imprezy/']")

    for c in cards:
        title = c.get_text(strip=True)

        # ❌ убираем мусор
        if not title or len(title) < 5:
            continue
        if "wstepwolny" in title.lower():
            continue

        href = c.get("href")
        if not href:
            continue

        url = href if href.startswith("http") else "https://www.trojmiasto.pl" + href

        # картинка (если есть)
        img_tag = c.find("img")
        img = img_tag.get("src") if img_tag else None

        address = "Trójmiasto"

        events.append({
            "title": title,
            "url": url,
            "img": img,
            "address": address
        })

    # убираем дубликаты
    unique = []
    seen = set()

    for e in events:
        if e["url"] in seen:
            continue
        seen.add(e["url"])
        unique.append(e)

    return unique


def send():
    events = get_events()

    if not events:
        bot.send_message(CHAT_ID, "Сегодня бесплатных мероприятий не найдено")
        return

    for e in events[:5]:
        text = f"""🎉 {e['title']}

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
