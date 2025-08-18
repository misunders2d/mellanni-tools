import os, requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = 330959414
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_telegram_message(message):
    """Send a message to Telegram."""
    try:
        response = requests.post(
            TELEGRAM_API_URL, json={"chat_id": CHAT_ID, "text": message}
        )
        response.raise_for_status()
        print("Telegram notification sent successfully.")
    except requests.RequestException as e:
        print(f"Failed to send Telegram notification: {e}")
