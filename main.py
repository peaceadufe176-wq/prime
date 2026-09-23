import os
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify
import requests

# === CONFIGURATION ===
TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 8080))
DATA_FILE = 'prime_users.json'

# === YOUR CHANNEL LINKS ===
TELEGRAM_CHANNEL = "https://t.me/+Yr8yI8DrvLkyYzA0"
WHATSAPP_LINK = "https://whatsapp.com/channel/0029Vb5ZFQTHAdNcCXSdtg0E"

# === YOUR BANNER IMAGE (correct URL) ===
BANNER_URL = "https://raw.githubusercontent.com/peaceadufe176-wq/prime/main/prime_banner.jpg"

# === TIMING SETTINGS ===
DELAY_BEFORE_CONTENT = 5      # Seconds before sending content
REMINDER_DELAY = 2 * 60 * 60  # 2 hours

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === STORAGE ===
class Storage:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_data(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Save error: {e}")

    def get_user(self, user_id):
        if user_id not in self.data:
            self.data[user_id] = {
                'user_id': user_id,
                'reminder_sent': False,
                'reminder_time': None,
                'username': '',
                'first_name': '',
                'last_name': '',
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            self._save_data()
        return self.data[user_id]

    def save_user(self, user_id, data):
        self.data[user_id] = data
        self._save_data()

    def get_all_users(self):
        return self.data

storage = Storage()

# === TELEGRAM API HELPERS ===
def send_photo(chat_id, photo_url, caption="", parse_mode='Markdown'):
    """Send photo with optional caption"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        'chat_id': chat_id,
        'photo': photo_url
    }
    if caption:
        payload['caption'] = caption
        payload['parse_mode'] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            logger.info(f"✅ Photo sent to {chat_id}")
            return response.json()
        else:
            logger.error(f"❌ Photo failed: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Send photo error: {e}")
        return None

def send_message(chat_id, text, parse_mode='Markdown'):
    """Send text message"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Message sent to {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get('result', [])
        return []
    except Exception as e:
        logger.error(f"Get updates error: {e}")
        return []

def delete_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Webhook deleted: {response.json()}")
        return response.json().get('ok', False)
    except Exception as e:
        logger.error(f"Delete webhook error: {e}")
        return False

# === CONTENT MESSAGE ===
def get_content_message(first_name=""):
    greeting = f"Hey {first_name}! 👋\n\n" if first_name else ""
    return f"""
{greeting}🤖 *Billionaires Forex Academy*

📈 Get forex education, market insights, trading updates, and information about our automated trading tools.
💡 Learn smarter. Trade with discipline. Stay informed.

📲 *Join our communities:*
🔵 *Telegram:*
{TELEGRAM_CHANNEL}

🟢 *WhatsApp Channel:*
{WHATSAPP_LINK}

⚠️ Forex trading involves risk. Past performance does not guarantee future results.
"""

# === REMINDER SYSTEM ===
def schedule_reminder(chat_id, user_id, first_name):
    """Schedule a 2-hour reminder"""
    def reminder_worker():
        logger.info(f"⏰ Reminder thread started for {user_id}, waiting 2 hours...")
        time.sleep(REMINDER_DELAY)

        try:
            # Send banner image first
            send_photo(chat_id, BANNER_URL)

            # Wait 3 seconds then send content
            time.sleep(3)
            send_message(chat_id, get_content_message(first_name))
            logger.info(f"✅ Reminder sent to {chat_id}")

            user = storage.get_user(str(user_id))
            user['reminder_sent'] = True
            user['reminder_time'] = datetime.now().isoformat()
            storage.save_user(str(user_id), user)

        except Exception as e:
            logger.error(f"Reminder error: {e}")

    thread = threading.Thread(target=reminder_worker, daemon=True)
    thread.start()
    logger.info(f"⏰ Reminder scheduled for {chat_id} in 2 hours")

# === MAIN WELCOME FLOW ===
def handle_start(chat_id, user_data):
    """
    1. Send image
    2. Wait 5 seconds
    3. Send content with links
    4. Schedule 2-hour reminder
    """
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    user['username'] = user_data.get('username', '')
    user['first_name'] = user_data.get('first_name', 'User')
    user['last_name'] = user_data.get('last_name', '')
    user['last_active'] = datetime.now().isoformat()
    storage.save_user(user_id, user)

    first_name = user['first_name']

    # === STEP 1: Send image first ===
    logger.info(f"📤 Step 1: Sending image to {chat_id}")
    send_photo(chat_id, BANNER_URL)

    # === STEP 2: Wait 5 seconds ===
    logger.info(f"⏳ Step 2: Waiting {DELAY_BEFORE_CONTENT} seconds...")
    time.sleep(DELAY_BEFORE_CONTENT)

    # === STEP 3: Send content with links ===
    logger.info(f"📤 Step 3: Sending content to {chat_id}")
    send_message(chat_id, get_content_message())

    # === STEP 4: Schedule 2-hour reminder ===
    if not user.get('reminder_sent', False):
        schedule_reminder(chat_id, user_id, first_name)

# === POLLING ===
def process_updates():
    last_update_id = 0
    logger.info("Starting polling loop...")

    delete_webhook()

    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)

            for update in updates:
                update_id = update.get('update_id')
                if update_id:
                    last_update_id = update_id

                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']
                    user_data = msg.get('from', {})

                    if 'text' in msg:
                        text = msg['text']
                        logger.info(f"Command from {chat_id}: {text}")

                        if text.startswith('/start'):
                            handle_start(chat_id, user_data)
                        else:
                            # For any other message, send image + content
                            send_photo(chat_id, BANNER_URL)
                            time.sleep(3)
                            send_message(chat_id, get_content_message())

            time.sleep(2)

        except Exception as e:
            logger.error(f"Process updates error: {e}")
            time.sleep(5)

# === FLASK ===
app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    all_users = storage.get_all_users()
    return f"""
    <h1>🌟 Billionaires Forex Academy Bot</h1>
    <p>Bot is running!</p>
    <p>Users: {len(all_users)}</p>
    <p>Status: ✅ Active</p>
    """

@app.route('/stats', methods=['GET'])
def stats_route():
    all_users = storage.get_all_users()
    return jsonify({
        'users': len(all_users),
        'reminders_sent': sum(1 for d in all_users.values() if d.get('reminder_sent', False))
    })

# === MAIN ===
def main():
    logger.info("=" * 50)
    logger.info("Starting Billionaires Forex Academy Bot...")
    logger.info(f"Telegram: {TELEGRAM_CHANNEL}")
    logger.info(f"WhatsApp: {WHATSAPP_LINK}")
    logger.info(f"Banner: {BANNER_URL}")
    logger.info(f"Content delay: {DELAY_BEFORE_CONTENT} seconds")
    logger.info(f"Reminder: {REMINDER_DELAY // 3600} hours")
    logger.info("=" * 50)

    poll_thread = threading.Thread(target=process_updates, daemon=True)
    poll_thread.start()
    logger.info("Polling thread started")

    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
