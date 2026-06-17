import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

URL = "https://www.trojmiasto.pl/imprezy/kalendarz-imprez/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_events():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    events = []

    # ищем все возможные карточки событий
    cards = soup.select("article, .event, .impreza, .box, li")

    for c in cards:
        text = c.get_text(" ", strip=True).lower()

        # фильтр: только бесплатные
        if "wstęp wolny" not in text and "bezpłat" not in text:
            continue

        title_tag = c.find(["h2", "h3"])
        title = title_tag.get_text(strip=True) if title_tag else "Bez tytułu"

        link_tag = c.find("a")
        url = None
        if link_tag and link_tag.get("href"):
            href = link_tag["href"]
            url = href if href.startswith("http") else "https://www.trojmiasto.pl" + href

        img_tag = c.find("img")
        img = None
        if img_tag:
            img = img_tag.get("src") or img_tag.get("data-src")

        address = "📍 Trójmiasto"

        events.append({
            "title": title,
            "url": url,
            "img": img,
            "address": address
        })

    return events


def send():
    events = get_events()

    if not events:
        bot.send_message(CHAT_ID, "Сегодня бесплатных мероприятий не найдено")
        return

    for e in events[:10]:
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
