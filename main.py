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

# === YOUR BANNER IMAGE ===
# ⚠️ REPLACE YOUR_USERNAME WITH YOUR GITHUB USERNAME
BANNER_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/prime-rewards-bot/main/assets/prime_banner.jpg"

# === REMINDER SETTINGS ===
REMINDER_DELAY = 2 * 60 * 60  # 2 hours in seconds

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
                'points': 0,
                'total_earned': 0,
                'prime_tier': 0,
                'prime_expiry': None,
                'daily_streak': 0,
                'last_daily': None,
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
def send_photo(chat_id, photo_url, caption, parse_mode='Markdown'):
    """Send photo with caption"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': parse_mode
        }, timeout=15)
        if response.status_code == 200:
            logger.info(f"Photo sent to {chat_id}")
        else:
            logger.error(f"Photo failed: {response.text}")
        return response.json()
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
            'parse_mode': parse_mode
        }, timeout=10)
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
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

# === PRIME SYSTEM ===
PRIME_TIERS = {
    0: {'name': 'Free', 'emoji': '🔓', 'price': 0, 'duration': 0},
    1: {'name': 'Basic Prime', 'emoji': '⭐', 'price': 50, 'duration': 7},
    2: {'name': 'Premium Prime', 'emoji': '💎', 'price': 150, 'duration': 14},
    3: {'name': 'Ultimate Prime', 'emoji': '👑', 'price': 300, 'duration': 30}
}

def get_prime_info(tier):
    return PRIME_TIERS.get(tier, PRIME_TIERS[0])

def is_prime_active(user):
    if not user.get('prime_expiry'):
        return False
    try:
        expiry = datetime.fromisoformat(user['prime_expiry'])
        return datetime.now() < expiry and user.get('prime_tier', 0) > 0
    except:
        return False

def get_prime_days_left(user):
    if not user.get('prime_expiry'):
        return 0
    try:
        expiry = datetime.fromisoformat(user['prime_expiry'])
        diff = expiry - datetime.now()
        return max(0, diff.days)
    except:
        return 0

def get_time_until(iso_time):
    if not iso_time:
        return "Available now!"
    try:
        last = datetime.fromisoformat(iso_time)
        next_time = last + timedelta(hours=24)
        now = datetime.now()
        if now >= next_time:
            return "Available now!"
        diff = next_time - now
        h = diff.seconds // 3600
        m = (diff.seconds % 3600) // 60
        return f"{h}h {m}m"
    except:
        return "Available now!"

# === REMINDER SYSTEM ===
def schedule_reminder(chat_id, user_id, first_name):
    """Schedule a 2-hour reminder for the user"""
    def reminder_worker():
        logger.info(f"⏰ Reminder thread started for {user_id}, waiting 2 hours...")
        time.sleep(REMINDER_DELAY)
        
        try:
            send_photo(
                chat_id,
                BANNER_URL,
                f"""
⏰ *REMINDER!*

Hey {first_name}! 👋

🤖 *Billionaires Forex Academy*

📈 Get forex education, market insights, trading updates, and information about our automated trading tools.
💡 Learn smarter. Trade with discipline. Stay informed.

📲 *Join our communities:*
🔵 *Telegram:*
{TELEGRAM_CHANNEL}

🟢 *WhatsApp Channel:*
{WHATSAPP_LINK}

⚠️ Forex trading involves risk. Past performance does not guarantee future results.

🔥 *Use /daily to claim your reward!* 🎁
                """
            )
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

# === COMMAND HANDLERS ===
def handle_start(chat_id, user_data):
    """New user starts the bot - send banner + links + schedule reminder"""
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    user['username'] = user_data.get('username', '')
    user['first_name'] = user_data.get('first_name', 'User')
    user['last_name'] = user_data.get('last_name', '')
    user['last_active'] = datetime.now().isoformat()
    storage.save_user(user_id, user)
    
    first_name = user['first_name']
    
    # === STEP 1: Send banner image with welcome ===
    welcome_caption = f"""
👋 *Welcome to Prime Rewards, {first_name}!*

💎 Your journey to premium rewards starts here!

🎁 *What you get:*
• Daily rewards with bonus multipliers
• 3 Prime tiers to unlock
• Exclusive premium perks
• Weekly bonuses

*Starting your Prime experience...*
    """
    
    send_photo(chat_id, BANNER_URL, welcome_caption)
    time.sleep(1)
    
    # === STEP 2: Send Billionaires Forex Academy info ===
    send_message(
        chat_id,
        f"""
🤖 *Billionaires Forex Academy*

📈 Get forex education, market insights, trading updates, and information about our automated trading tools.
💡 Learn smarter. Trade with discipline. Stay informed.

📲 *Join our communities:*
🔵 *Telegram:*
{TELEGRAM_CHANNEL}

🟢 *WhatsApp Channel:*
{WHATSAPP_LINK}

⚠️ Forex trading involves risk. Past performance does not guarantee future results.
        """
    )
    time.sleep(1)
    
    # === STEP 3: Schedule 2-hour reminder ===
    if not user.get('reminder_sent', False):
        schedule_reminder(chat_id, user_id, first_name)
    
    # === STEP 4: Send command menu ===
    time.sleep(1)
    
    send_message(
        chat_id,
        f"""
📋 *AVAILABLE COMMANDS*

💰 *Rewards:*
/daily - Claim daily reward 📅
/prime - Check Prime status 🌟
/primeupgrade - Upgrade tier 📈
/profile - Your profile 👤
/leaderboard - Top players 🏆

📢 *Channels:*
/channels - View all channels 📱
/help - All commands 📚

🔥 *Use /daily to claim your first reward!*
        """
    )

def handle_channels(chat_id):
    """Send channels on demand"""
    send_photo(
        chat_id,
        BANNER_URL,
        f"""
🤖 *Billionaires Forex Academy*

📈 Get forex education, market insights, trading updates, and information about our automated trading tools.
💡 Learn smarter. Trade with discipline. Stay informed.

📲 *Join our communities:*
🔵 *Telegram:*
{TELEGRAM_CHANNEL}

🟢 *WhatsApp Channel:*
{WHATSAPP_LINK}

⚠️ Forex trading involves risk. Past performance does not guarantee future results.
        """
    )

def handle_daily(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    now = datetime.now()
    
    if user.get('last_daily'):
        try:
            last = datetime.fromisoformat(user['last_daily'])
            if now - last < timedelta(hours=24):
                time_left = get_time_until(user['last_daily'])
                send_message(
                    chat_id,
                    f"""
⏳ *Already Claimed Today!*
━━━━━━━━━━━━━━━━
🕐 Next claim in: {time_left}

📅 Streak: {user['daily_streak']} days
💪 Keep going!
                    """
                )
                return
        except:
            pass
    
    if user.get('last_daily'):
        try:
            last = datetime.fromisoformat(user['last_daily'])
            if now - last < timedelta(hours=48):
                user['daily_streak'] += 1
            else:
                user['daily_streak'] = 1
        except:
            user['daily_streak'] = 1
    else:
        user['daily_streak'] = 1
    
    base = 10
    prime_bonus = 0
    if is_prime_active(user):
        tier = user.get('prime_tier', 0)
        prime_bonus = {1: 5, 2: 10, 3: 20}.get(tier, 0)
    
    streak_bonus = (user['daily_streak'] // 7) * 5
    total = base + prime_bonus + streak_bonus
    
    user['points'] += total
    user['total_earned'] = user.get('total_earned', 0) + total
    user['last_daily'] = now.isoformat()
    storage.save_user(user_id, user)
    
    prime_info = get_prime_info(user.get('prime_tier', 0))
    
    send_message(
        chat_id,
        f"""
🎉 *Daily Reward Claimed!*
━━━━━━━━━━━━━━━━
💰 *+{total} points*
📊 Base: {base}
{prime_info['emoji']} Prime Bonus: +{prime_bonus}
📅 Streak: {user['daily_streak']} days

💵 Total: {user['points']} points

Come back tomorrow! 🚀
        """
    )

def handle_prime(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    tier = user.get('prime_tier', 0)
    prime_info = get_prime_info(tier)
    active = is_prime_active(user)
    days_left = get_prime_days_left(user)
    
    send_message(
        chat_id,
        f"""
🌟 *PRIME STATUS*
━━━━━━━━━━━━━━━━
{prime_info['emoji']} *Tier: {prime_info['name']}*
{'✅ Active' if active else '❌ Not Active'}
📅 Days Left: {days_left}

💰 Points: {user['points']}
📅 Streak: {user['daily_streak']} days

📈 *Upgrade Options:*
⭐ Basic Prime - 50 pts (7 days)
💎 Premium Prime - 150 pts (14 days)
👑 Ultimate Prime - 300 pts (30 days)

Use /primeupgrade to upgrade! 🚀
        """
    )

def handle_primeupgrade(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    
    current_tier = user.get('prime_tier', 0)
    next_tier = current_tier + 1 if current_tier < 3 else None
    
    if not next_tier:
        send_message(chat_id, "👑 You already have Ultimate Prime!")
        return
    
    tier_info = PRIME_TIERS[next_tier]
    
    if user['points'] < tier_info['price']:
        send_message(
            chat_id,
            f"""
❌ *Insufficient Points!*
━━━━━━━━━━━━━━━━
💰 Need: {tier_info['price']} points
💵 You have: {user['points']}
📊 Need {tier_info['price'] - user['points']} more

💡 Earn more by:
• Daily claims
• Streaks
            """
        )
        return
    
    user['points'] -= tier_info['price']
    user['prime_tier'] = next_tier
    user['prime_expiry'] = (datetime.now() + timedelta(days=tier_info['duration'])).isoformat()
    storage.save_user(user_id, user)
    
    send_message(
        chat_id,
        f"""
🎉 *Prime Upgrade Successful!*
━━━━━━━━━━━━━━━━
{tier_info['emoji']} *New Tier: {tier_info['name']}*
📅 Duration: {tier_info['duration']} days
💰 Points Remaining: {user['points']}

Enjoy your new Prime status! 🌟
        """
    )

def handle_profile(chat_id):
    user_id = str(chat_id)
    user = storage.get_user(user_id)
    tier = user.get('prime_tier', 0)
    prime_info = get_prime_info(tier)
    days_left = get_prime_days_left(user)
    
    send_message(
        chat_id,
        f"""
👤 *YOUR PROFILE*
━━━━━━━━━━━━━━━━
👤 {user.get('first_name', 'User')}
📛 @{user.get('username', 'N/A')}

{prime_info['emoji']} *Prime: {prime_info['name']}*
📅 Days Left: {days_left}

💰 Points: {user['points']}
⭐ Total Earned: {user.get('total_earned', 0)}
📅 Streak: {user['daily_streak']} days
        """
    )

def handle_leaderboard(chat_id):
    all_users = storage.get_all_users()
    sorted_users = sorted(
        [(uid, data) for uid, data in all_users.items()],
        key=lambda x: x[1].get('points', 0),
        reverse=True
    )[:10]
    
    if not sorted_users:
        send_message(chat_id, "No users yet! Be the first! 🏆")
        return
    
    message = "🏆 *PRIME LEADERBOARD*\n━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f"{i}."
        name = data.get('username', data.get('first_name', f"User{uid}"))
        points = data.get('points', 0)
        tier = get_prime_info(data.get('prime_tier', 0))
        message += f"{medal} @{name} {tier['emoji']} - {points} pts\n"
    
    send_message(chat_id, message)

def handle_help(chat_id):
    send_message(
        chat_id,
        """
📚 *PRIME REWARDS COMMANDS*
━━━━━━━━━━━━━━━━

💰 *Rewards:*
/daily - Claim daily reward
/prime - Check Prime status
/primeupgrade - Upgrade tier
/profile - Your profile
/leaderboard - Top players

📢 *Channels:*
/channels - View Telegram & WhatsApp

📊 *Prime Tiers:*
⭐ Basic - 50 pts (7 days)
💎 Premium - 150 pts (14 days)
👑 Ultimate - 300 pts (30 days)

💡 *Earn points daily with /daily!*
        """
    )

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
                        elif text.startswith('/help'):
                            handle_help(chat_id)
                        elif text.startswith('/channels'):
                            handle_channels(chat_id)
                        elif text.startswith('/daily'):
                            handle_daily(chat_id)
                        elif text.startswith('/prime'):
                            if text.startswith('/primeupgrade'):
                                handle_primeupgrade(chat_id)
                            else:
                                handle_prime(chat_id)
                        elif text.startswith('/profile'):
                            handle_profile(chat_id)
                        elif text.startswith('/leaderboard'):
                            handle_leaderboard(chat_id)
                        else:
                            send_message(
                                chat_id,
                                "❓ Unknown command. Use /help to see available commands."
                            )
            
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
    <h1>🌟 Prime Rewards Bot</h1>
    <p>Bot is running!</p>
    <p>Users: {len(all_users)}</p>
    <p>Telegram: {TELEGRAM_CHANNEL}</p>
    <p>WhatsApp: {WHATSAPP_LINK}</p>
    <p>Status: ✅ Active</p>
    """

@app.route('/stats', methods=['GET'])
def stats_route():
    all_users = storage.get_all_users()
    return jsonify({
        'users': len(all_users),
        'total_points': sum(data.get('points', 0) for data in all_users.values())
    })

# === MAIN ===
def main():
    logger.info("=" * 50)
    logger.info("Starting Prime Rewards Bot...")
    logger.info(f"Telegram: {TELEGRAM_CHANNEL}")
    logger.info(f"WhatsApp: {WHATSAPP_LINK}")
    logger.info(f"Banner: {BANNER_URL[:70]}...")
    logger.info(f"Reminder: {REMINDER_DELAY // 3600} hours")
    logger.info("=" * 50)
    
    poll_thread = threading.Thread(target=process_updates, daemon=True)
    poll_thread.start()
    logger.info("Polling thread started")
    
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()
