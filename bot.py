import json
import os
import random
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone as dt_timezone
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


print("BOOT: script started", flush=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def app_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(BASE_DIR, path)


def load_dotenv(path=None):
    path = path or app_path(".env")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value or not os.environ.get(key):
                os.environ[key] = value


load_dotenv()

DEFAULT_DB_PATH = app_path(os.path.join("data", "english_bot.sqlite3"))
LEGACY_DB_PATH = app_path("english_bot.sqlite3")
DB_PATH = app_path(os.getenv("BOT_DB_PATH", DEFAULT_DB_PATH))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")
OPENROUTER_API_URL = os.getenv(
    "OPENROUTER_API_URL",
    "https://openrouter.ai/api/v1/chat/completions",
)
OPENROUTER_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "30"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")
REMINDER_TIMES = [
    item.strip() for item in os.getenv("REMINDER_TIMES", "09:00,15:00,21:00").split(",") if item.strip()
]
WORD_OF_DAY_TIME = os.getenv("WORD_OF_DAY_TIME", "12:00")
WORD_OF_DAY_PATH = app_path(os.getenv("WORD_OF_DAY_PATH", "word_of_day.txt"))
CYRILLIC_MEME_REACTIONS = [
    {
        "image_path": app_path(os.path.join("assets", "cyrillic-confused.webp")),
        "caption": "\u0422\u044b \u043f\u043e-\u043c\u043e\u0435\u043c\u0443 \u043f\u0435\u0440\u0435\u043f\u0443\u0442\u0430\u043b",
    }
]
PRACTICE_BUTTON = "Practice"
NEXT_PRACTICE_BUTTON = "Next practice"
BACK_TO_MENU_BUTTON = "Back to menu"
PRACTICE_POSITIVE_REACTIONS = [
    "\u0412\u043e\u0442 \u044d\u0442\u043e \u0443\u0436\u0435 \u0437\u0432\u0443\u0447\u0438\u0442 \u0436\u0438\u0432\u043e \U0001f44c",
    "Good. \u042d\u0442\u043e \u0443\u0436\u0435 \u043d\u0435 \u0448\u043a\u043e\u043b\u044c\u043d\u044b\u0439 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439.",
    "\u041d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u043e \u0437\u0430\u0448\u043b\u043e. \u041d\u043e\u0441\u0438\u0442\u0435\u043b\u044c \u0431\u044b \u043f\u043e\u043d\u044f\u043b \u0431\u0435\u0437 \u043f\u0440\u043e\u0431\u043b\u0435\u043c.",
    "Nice. \u0423\u0436\u0435 \u0437\u0432\u0443\u0447\u0438\u0442 \u043a\u0430\u043a \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0439 \u0434\u0438\u0430\u043b\u043e\u0433.",
    "\u0414\u0430, \u044d\u0442\u043e \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442. \u041c\u043e\u0436\u043d\u043e \u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0443\u0442\u044c \u043e\u0442\u043f\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u0442\u044c.",
    "Solid answer. \u041c\u0430\u043b\u0435\u043d\u044c\u043a\u0438\u0439 \u0430\u043f\u0433\u0440\u0435\u0439\u0434 - \u0438 \u0432\u043e\u043e\u0431\u0449\u0435 \u043e\u0442\u043b\u0438\u0447\u043d\u043e.",
    "\u0412\u043e\u0442 \u044d\u0442\u043e \u0443\u0436\u0435 usable English.",
    "\u0425\u043e\u0440\u043e\u0448\u043e. \u041d\u0435 \u0438\u0434\u0435\u0430\u043b\u044c\u043d\u043e \u0443\u0447\u0435\u0431\u043d\u0438\u043a\u043e\u0432\u043e, \u0430 \u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u043e \u043f\u043e-\u0447\u0435\u043b\u043e\u0432\u0435\u0447\u0435\u0441\u043a\u0438.",
    "Yep, this works. \u0414\u043e\u0431\u0430\u0432\u0438\u043c \u0447\u0443\u0442\u044c natural vibe.",
    "\u0423\u0436\u0435 \u0431\u043b\u0438\u0437\u043a\u043e. \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0437\u0432\u0443\u0447\u0430\u043d\u0438\u0435 \u043c\u044f\u0433\u0447\u0435.",
]
PRACTICE_SCENARIOS = [
    {
        "id": "l1_late",
        "level": 1,
        "situation": "You are late. Say sorry in English.",
        "keywords": ("sorry", "late"),
        "natural": "Sorry I'm late.",
        "better": "Sorry, I'm a bit late.",
        "why": "'Sorry I'm late' is short, normal, and enough.",
        "vocab": [
            {"word": "late", "translation": "опоздавший / поздно", "example": "I'm late for work."},
            {"word": "sorry", "translation": "извини / простите", "example": "Sorry, I'm late."},
        ],
    },
    {
        "id": "l1_coffee",
        "level": 1,
        "situation": "Ask for coffee.",
        "keywords": ("coffee", "can", "please"),
        "natural": "Can I get a coffee, please?",
        "better": "Could I get a coffee, please?",
        "why": "'Can I get...' is simple and works in cafes.",
        "vocab": [
            {"word": "coffee", "translation": "кофе", "example": "Can I get a coffee?"},
            {"word": "please", "translation": "пожалуйста", "example": "A coffee, please."},
        ],
    },
    {
        "id": "l1_repeat",
        "level": 1,
        "situation": "Ask someone to repeat.",
        "keywords": ("repeat", "again", "sorry"),
        "natural": "Sorry, can you repeat that?",
        "better": "Sorry, could you say that again?",
        "why": "Simple, polite, and nobody feels awkward.",
        "vocab": [
            {"word": "repeat", "translation": "повторить", "example": "Can you repeat that?"},
            {"word": "again", "translation": "ещё раз / снова", "example": "Say that again, please."},
        ],
    },
    {
        "id": "l1_tired",
        "level": 1,
        "situation": "Say you are tired.",
        "keywords": ("tired", "am", "i'm"),
        "natural": "I'm tired.",
        "better": "I'm pretty tired today.",
        "why": "'Pretty tired' sounds casual and human.",
        "vocab": [
            {"word": "tired", "translation": "уставший", "example": "I'm tired today."},
            {"word": "pretty tired", "translation": "довольно уставший", "example": "I'm pretty tired."},
        ],
    },
    {
        "id": "l2_oat_milk",
        "level": 2,
        "situation": "You want oat milk in your coffee.",
        "keywords": ("oat", "milk", "could", "can"),
        "natural": "Could I get that with oat milk?",
        "better": "Could you make it with oat milk, please?",
        "why": "'Could I get...' is casual, polite, and very coffee-shop native.",
        "vocab": [
            {"word": "oat milk", "translation": "овсяное молоко", "example": "Could I get oat milk?"},
            {"word": "could I get", "translation": "можно мне / я бы хотел", "example": "Could I get a latte?"},
        ],
    },
    {
        "id": "l2_help",
        "level": 2,
        "situation": "Ask a colleague for help.",
        "keywords": ("help", "could", "can", "minute"),
        "natural": "Could you help me with this?",
        "better": "Do you have a minute to help me with this?",
        "why": "'Do you have a minute...' respects their time and sounds relaxed.",
        "vocab": [
            {"word": "help me", "translation": "помочь мне", "example": "Can you help me?"},
            {"word": "a minute", "translation": "минутка", "example": "Do you have a minute?"},
        ],
    },
    {
        "id": "l3_decline",
        "level": 3,
        "situation": "Politely decline an invitation.",
        "keywords": ("can't", "cannot", "sorry", "make", "thanks"),
        "natural": "Thanks for inviting me, but I can't make it.",
        "better": "I'd love to, but I can't make it this time.",
        "why": "'I can't make it' is the smooth everyday way to decline plans.",
        "vocab": [
            {"word": "can't make it", "translation": "не смогу прийти / не получится", "example": "Sorry, I can't make it."},
            {"word": "I'd love to", "translation": "я бы с радостью", "example": "I'd love to, but I'm busy."},
        ],
    },
    {
        "id": "l3_running_late",
        "level": 3,
        "situation": "You are late to a meeting and want to sound natural.",
        "keywords": ("sorry", "running", "late"),
        "natural": "Sorry, I'm running late.",
        "better": "Sorry, I'm running a bit late. I'll be there soon.",
        "why": "'running late' is the real-life phrase people use.",
        "vocab": [
            {"word": "running late", "translation": "опаздываю", "example": "I'm running late."},
            {"word": "soon", "translation": "скоро", "example": "I'll be there soon."},
        ],
    },
    {
        "id": "l4_small_talk",
        "level": 4,
        "situation": "You are making small talk with someone you just met.",
        "keywords": ("nice", "meet", "how", "know"),
        "natural": "Nice to meet you. How do you know everyone here?",
        "better": "Nice to meet you. How do you know the host?",
        "why": "This gives the other person an easy way into the conversation.",
        "vocab": [
            {"word": "small talk", "translation": "лёгкая светская беседа", "example": "I'm bad at small talk."},
            {"word": "host", "translation": "хозяин / организатор", "example": "How do you know the host?"},
        ],
    },
]
TIMEZONE_ALIASES = {
    "Europe/Moscow": "+03:00",
    "Europe/London": "+00:00",
    "Europe/Berlin": "+01:00",
    "Asia/Dubai": "+04:00",
    "Asia/Yerevan": "+04:00",
    "Asia/Tbilisi": "+04:00",
    "Asia/Almaty": "+05:00",
    "Asia/Tashkent": "+05:00",
    "Asia/Bangkok": "+07:00",
    "Asia/Shanghai": "+08:00",
    "Asia/Tokyo": "+09:00",
    "America/New_York": "-05:00",
    "America/Chicago": "-06:00",
    "America/Denver": "-07:00",
    "America/Los_Angeles": "-08:00",
}


def prepare_db_file():
    if DB_PATH == ":memory:":
        return

    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    if DB_PATH != LEGACY_DB_PATH and not os.path.exists(DB_PATH) and os.path.exists(LEGACY_DB_PATH):
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)


prepare_db_file()


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                first_seen_at TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Europe/Moscow'
            )
            """
        )
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "timezone" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Europe/Moscow'"
            )
        if "practice_mode" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN practice_mode INTEGER NOT NULL DEFAULT 0"
            )
        if "current_practice_scenario" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN current_practice_scenario TEXT"
            )
        if "practice_level" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN practice_level INTEGER NOT NULL DEFAULT 1"
            )
        if "practice_correct_count" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN practice_correct_count INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                normalized_word TEXT NOT NULL,
                translation TEXT NOT NULL,
                phrase_en TEXT NOT NULL,
                phrase_ru TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_sent_at TEXT,
                times_sent INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, normalized_word)
            )
            """
        )
        word_columns = [row["name"] for row in conn.execute("PRAGMA table_info(words)").fetchall()]
        if "learned_from_practice" not in word_columns:
            conn.execute(
                "ALTER TABLE words ADD COLUMN learned_from_practice INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_log (
                user_id INTEGER NOT NULL,
                slot_date TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                PRIMARY KEY(user_id, slot_date, slot_time)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS word_of_day_log (
                user_id INTEGER NOT NULL,
                slot_date TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                PRIMARY KEY(user_id, slot_date)
            )
            """
        )


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def fixed_timezone(value):
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", value.strip())
    if not match:
        return None

    sign, hours, minutes = match.groups()
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    if sign == "-":
        delta = -delta
    return dt_timezone(delta)


def resolve_timezone(value):
    value = (value or DEFAULT_TIMEZONE).strip()
    alias = TIMEZONE_ALIASES.get(value)
    if alias:
        return fixed_timezone(alias)

    fixed = fixed_timezone(value)
    if fixed:
        return fixed

    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return None


def valid_timezone(timezone):
    return resolve_timezone(timezone) is not None


def user_local_now(timezone):
    tz = resolve_timezone(timezone) or resolve_timezone(DEFAULT_TIMEZONE) or dt_timezone.utc
    return datetime.now(tz)


def normalize_word(text):
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


INVALID_ENGLISH_MESSAGE = (
    "\u041f\u043e\u0445\u043e\u0436\u0435, \u044d\u0442\u043e \u043d\u0435 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u043e\u0435 \u0441\u043b\u043e\u0432\u043e. "
    "\u041e\u0442\u043f\u0440\u0430\u0432\u044c \u0441\u043b\u043e\u0432\u043e \u0438\u043b\u0438 \u0444\u0440\u0430\u0437\u0443 \u043d\u0430 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u043e\u043c - "
    "\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: awkward, deadline, overthinking."
)
TRANSLITERATED_RUSSIAN_WORDS = {
    "privet",
    "spasibo",
    "pozhaluysta",
    "poka",
    "dver",
    "okno",
    "stol",
    "stul",
    "dom",
    "kot",
    "sobaka",
    "chelovek",
    "rabota",
    "den",
    "noch",
    "utro",
    "vecher",
    "horosho",
    "ploho",
}


def is_valid_english_input(text):
    value = normalize_word(text)
    if not value or re.search(r"[\u0400-\u04ff]", value):
        return False
    if not value or re.search(r"[А-Яа-яЁё]", value):
        return False
    if not re.search(r"[a-z]", value):
        return False
    if re.search(r"[^a-z\s'\-]", value):
        return False

    words = re.findall(r"[a-z]+(?:['-][a-z]+)?", value)
    if not words:
        return False
    if any(word in TRANSLITERATED_RUSSIAN_WORDS for word in words):
        return False
    if len(words) == 1 and re.search(r"(asdf|sdfg|dfgh|qwer|wert|zxcv|hjkl)", words[0]):
        return False
    if len(words) == 1 and len(words[0]) > 3 and not re.search(r"[aeiouy]", words[0]):
        return False
    if len(words) == 1 and re.search(r"(.)\1\1", words[0]):
        return False
    if len(words) == 1 and re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", words[0]):
        return False
    return True


def looks_like_valid_english(text):
    return is_valid_english_input(text)


def contains_cyrillic(text):
    return bool(re.search(r"[\u0400-\u04ff]", text or ""))


CONTEXT_EMOJI_RULES = [
    ("\U0001f4bb", ("code", "coding", "program", "computer", "software", "app", "debug", "data", "algorithm")),
    ("\U0001f4bc", ("work", "job", "career", "office", "business", "meeting", "deadline", "project", "client")),
    ("\U0001f4b0", ("money", "cash", "price", "cost", "pay", "salary", "bank", "budget", "profit", "finance")),
    ("\U0001f3e0", ("home", "house", "room", "kitchen", "family", "parent", "mother", "father")),
    ("\U0001f697", ("car", "drive", "road", "traffic", "train", "bus", "flight", "airport", "travel", "trip")),
    ("\U0001f37d\ufe0f", ("food", "eat", "drink", "coffee", "tea", "breakfast", "lunch", "dinner", "restaurant")),
    ("\U0001f3c3", ("run", "sport", "gym", "fitness", "health", "exercise", "game", "football", "swim")),
    ("\U0001f3a8", ("art", "music", "movie", "book", "story", "paint", "design", "photo", "creative")),
    ("\U0001f48c", ("love", "friend", "date", "relationship", "feel", "emotion", "happy", "sad", "angry")),
    ("\U0001f4da", ("learn", "study", "school", "university", "lesson", "exam", "knowledge", "grammar")),
    ("\U0001f30d", ("world", "country", "city", "nature", "weather", "sea", "mountain", "forest", "river")),
    ("\U0001f527", ("make", "build", "fix", "repair", "tool", "create", "change", "improve")),
]


def sanitize_emoji(value):
    emoji = str(value or "").strip().split(maxsplit=1)[0] if value else ""
    if not emoji or len(emoji) > 8:
        return ""
    if re.search(r"[A-Za-z0-9<>&]", emoji):
        return ""
    return emoji


def choose_context_emoji(card):
    explicit = sanitize_emoji(card.get("emoji") or card.get("emoji_context"))
    if explicit:
        return explicit

    context = " ".join(
        str(card.get(key) or "").lower()
        for key in ("word", "translation", "translation_ru", "phrase_en", "phrase_ru")
    )
    for emoji, keywords in CONTEXT_EMOJI_RULES:
        if any(re.search(rf"\b{re.escape(keyword)}\b", context) for keyword in keywords):
            return emoji
    return "\U0001f9e0"


def telegram_request(method, payload=None):
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    data = urllib.parse.urlencode(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result["result"]


def telegram_multipart_request(method, fields, files):
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    boundary = f"----english-bot-{int(time.time() * 1000)}"
    body = bytearray()

    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for key, file_path in files.items():
        filename = os.path.basename(file_path)
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(b"Content-Type: image/webp\r\n\r\n")
        with open(file_path, "rb") as file_obj:
            body.extend(file_obj.read())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        raw_body = response.read().decode("utf-8")
    result = json.loads(raw_body)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result["result"]


def send_message(chat_id, text, reply_markup=None):
    if os.getenv("LOCAL_TEST") == "1":
        safe_text = f"\nBOT -> {chat_id}\n{text}\n"
        encoding = sys.stdout.encoding or "utf-8"
        print(safe_text.encode(encoding, errors="replace").decode(encoding))
        return {"message_id": 0}

    return telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "reply_markup": json.dumps(reply_markup or main_keyboard(), ensure_ascii=False),
        },
    )


def send_photo(chat_id, image_path):
    if os.getenv("LOCAL_TEST") == "1":
        safe_text = f"\nBOT PHOTO -> {chat_id}\n{image_path}\n"
        encoding = sys.stdout.encoding or "utf-8"
        print(safe_text.encode(encoding, errors="replace").decode(encoding))
        return {"message_id": 0}

    return telegram_multipart_request(
        "sendPhoto",
        {
            "chat_id": chat_id,
            "reply_markup": json.dumps(main_keyboard(), ensure_ascii=False),
        },
        {"photo": image_path},
    )


def send_cyrillic_meme_reaction(chat_id):
    reaction = CYRILLIC_MEME_REACTIONS[0]
    send_photo(chat_id, reaction["image_path"])
    send_message(chat_id, reaction["caption"])


def main_keyboard():
    return {
        "keyboard": [[{"text": "\u0428\u0430\u0440\u044e"}, {"text": PRACTICE_BUTTON}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def practice_keyboard():
    return {
        "keyboard": [[{"text": NEXT_PRACTICE_BUTTON}, {"text": BACK_TO_MENU_BUTTON}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def practice_vocab_keyboard(scenario):
    buttons = [
        {
            "text": item["word"],
            "callback_data": f"pv:{scenario['id']}:{index}",
        }
        for index, item in enumerate(scenario.get("vocab", [])[:3])
    ]
    return {"inline_keyboard": [buttons]} if buttons else None


def word_card_prompt(word):
    return (
        "You are a warm, modern English companion for adult Russian speakers. "
        "Return only valid JSON with keys: is_valid_english, word, translation_ru, "
        "phrase_en, phrase_ru, usage_note_ru, emoji. "
        "First decide if the input is a real English word or phrase. Reject Russian "
        "written in Latin letters, typos, gibberish, and non-English input. "
        "Examples to reject: Dver, privet, spasibo. Do not translate them into English. "
        "If invalid, set is_valid_english to false and leave all text fields empty. "
        "If valid, write like a warm, modern English companion, not a dictionary: "
        "natural Russian meaning, one lively real-life English example, natural Russian "
        "translation, and a short Russian note about when people actually use it. "
        "Tone: modern, witty, adult casual; not textbook, not childish slang, not TikTok brainrot. "
        "Avoid boring examples like beach-day textbook sentences. Use work, relationships, "
        "awkward moments, daily life, real conversations. Choose one relevant emoji.\n\n"
        f"Input: {word}"
    )


def word_card_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "is_valid_english": {
                "type": "boolean",
                "description": "True only for a real English word or phrase.",
            },
            "word": {
                "type": "string",
                "description": "The English word or phrase.",
            },
            "translation_ru": {
                "type": "string",
                "description": "A concise Russian translation.",
            },
            "phrase_en": {
                "type": "string",
                "description": "A natural English example sentence using the word.",
            },
            "phrase_ru": {
                "type": "string",
                "description": "Russian translation of phrase_en.",
            },
            "usage_note_ru": {
                "type": "string",
                "description": "Short Russian note: when people actually use this word or phrase.",
            },
            "emoji": {
                "type": "string",
                "description": "One emoji matching the word's context or meaning.",
            },
        },
        "required": [
            "is_valid_english",
            "word",
            "translation_ru",
            "phrase_en",
            "phrase_ru",
            "usage_note_ru",
            "emoji",
        ],
    }


def normalize_card(card, word):
    is_valid = bool(card.get("is_valid_english", True))
    normalized = {
        "is_valid_english": is_valid,
        "word": str(card.get("word") or word).strip(),
        "translation": str(card.get("translation_ru") or card.get("translation") or "").strip(),
        "phrase_en": str(card.get("phrase_en") or "").strip(),
        "phrase_ru": str(card.get("phrase_ru") or "").strip(),
        "usage_note": str(card.get("usage_note_ru") or card.get("usage_note") or "").strip(),
        "emoji": sanitize_emoji(card.get("emoji") or card.get("emoji_context")),
    }
    normalized["emoji"] = normalized["emoji"] or choose_context_emoji(normalized)
    return normalized


def safe_error_body(error):
    try:
        return error.read().decode("utf-8", errors="replace")[:1000]
    except Exception:
        return ""


def preview_body(text, limit=1000):
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def log_provider_error(provider, exc):
    if isinstance(exc, urllib.error.HTTPError):
        body = safe_error_body(exc)
        print(f"{provider} error: HTTP {exc.code} {exc.reason}", flush=True)
        print(f"{provider} response body: {body}", flush=True)
        return
    print(f"{provider} error: {type(exc).__name__}: {exc}", flush=True)


def openrouter_word_card(word):
    if not OPENROUTER_API_KEY:
        print("OpenRouter skipped: OPENROUTER_API_KEY is empty", flush=True)
        return None

    print(
        f"BOOT: requesting openrouter model={OPENROUTER_MODEL} timeout={OPENROUTER_TIMEOUT}",
        flush=True,
    )
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": word_card_prompt(word),
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "word_card",
                "strict": True,
                "schema": word_card_schema(),
            },
        },
    }
    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://english-telegram-bot.local",
            "X-Title": "English Telegram Bot",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            print(f"BOOT: openrouter response status={response.status}", flush=True)
            print(f"OpenRouter response body: {preview_body(raw_body)}", flush=True)
            data = json.loads(raw_body)
    except urllib.error.HTTPError as exc:
        print("OPENROUTER HTTP ERROR:", exc, flush=True)
        log_provider_error("OpenRouter", exc)
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        print("OPENROUTER NETWORK/TIMEOUT ERROR:", exc, flush=True)
        log_provider_error("OpenRouter", exc)
        return None
    except Exception as exc:
        print("OPENROUTER ERROR:", exc, flush=True)
        log_provider_error("OpenRouter", exc)
        return None

    choices = data.get("choices", [])
    if not choices:
        print(f"OpenRouter error: no choices in response: {data}", flush=True)
        return None

    message = choices[0].get("message", {})
    text = message.get("content", "")
    if isinstance(text, list):
        text = "".join(item.get("text", "") for item in text if isinstance(item, dict))
    text = str(text).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)

    try:
        card = json.loads(text)
    except json.JSONDecodeError:
        return None

    return normalize_card(card, word)


def fallback_word_card(word):
    clean_word = word.strip()
    card = {
        "is_valid_english": is_valid_english_input(clean_word),
        "word": clean_word,
        "translation": "add OPENROUTER_API_KEY for automatic translation",
        "phrase_en": f"I almost used '{clean_word}' in a meeting, then decided to sound like a person instead.",
        "phrase_ru": f"\u042f \u0447\u0443\u0442\u044c \u043d\u0435 \u0432\u0441\u0442\u0430\u0432\u0438\u043b '{clean_word}' \u043d\u0430 \u0441\u043e\u0432\u0435\u0449\u0430\u043d\u0438\u0438, \u043d\u043e \u0440\u0435\u0448\u0438\u043b \u0432\u0441\u0435-\u0442\u0430\u043a\u0438 \u0437\u0432\u0443\u0447\u0430\u0442\u044c \u043a\u0430\u043a \u0447\u0435\u043b\u043e\u0432\u0435\u043a.",
        "usage_note": "\u041a\u043e\u0433\u0434\u0430 \u043d\u0443\u0436\u043d\u043e \u0432\u0441\u0442\u0440\u0435\u0442\u0438\u0442\u044c \u0441\u043b\u043e\u0432\u043e \u0432 \u0436\u0438\u0432\u043e\u043c \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0435, \u0430 \u043d\u0435 \u0432 \u0441\u0443\u0445\u043e\u043c \u0441\u043b\u043e\u0432\u0430\u0440\u0435.",
    }
    card["emoji"] = choose_context_emoji(card)
    return card


def build_word_card(word):
    if not is_valid_english_input(word):
        return {"is_valid_english": False}

    card = openrouter_word_card(word) or fallback_word_card(word)
    if not card.get("is_valid_english", True):
        return card
    if not card["translation"] or not card["phrase_en"] or not card["phrase_ru"]:
        return fallback_word_card(word)
    return card


def remember_user(user_id, chat_id):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO users(user_id, chat_id, first_seen_at, timezone)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET chat_id = excluded.chat_id
            """,
            (user_id, chat_id, now_iso(), DEFAULT_TIMEZONE),
        )


def set_user_timezone(user_id, timezone):
    with db_connect() as conn:
        conn.execute(
            "UPDATE users SET timezone = ? WHERE user_id = ?",
            (timezone, user_id),
        )


def get_user_practice_state(user_id):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT practice_mode, current_practice_scenario, practice_level, practice_correct_count
            FROM users
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return {
            "practice_mode": False,
            "current_practice_scenario": None,
            "practice_level": 1,
            "practice_correct_count": 0,
        }
    return {
        "practice_mode": bool(row["practice_mode"]),
        "current_practice_scenario": row["current_practice_scenario"],
        "practice_level": row["practice_level"] or 1,
        "practice_correct_count": row["practice_correct_count"] or 0,
    }


def set_practice_state(user_id, practice_mode, scenario_id=None):
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET practice_mode = ?, current_practice_scenario = ?
            WHERE user_id = ?
            """,
            (1 if practice_mode else 0, scenario_id, user_id),
        )


def record_practice_result(user_id, is_good):
    state = get_user_practice_state(user_id)
    level = min(max(int(state.get("practice_level") or 1), 1), 4)
    correct_count = int(state.get("practice_correct_count") or 0)
    if is_good:
        correct_count += 1
        if correct_count >= 3 and level < 4:
            level += 1
            correct_count = 0

    with db_connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET practice_level = ?, practice_correct_count = ?
            WHERE user_id = ?
            """,
            (level, correct_count, user_id),
        )


def save_word(user_id, card):
    normalized = normalize_word(card["word"])
    learned_from_practice = 1 if card.get("learned_from_practice") else 0
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO words(user_id, word, normalized_word, translation, phrase_en, phrase_ru, created_at, learned_from_practice)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, normalized_word) DO UPDATE SET
                translation = excluded.translation,
                phrase_en = excluded.phrase_en,
                phrase_ru = excluded.phrase_ru,
                learned_from_practice = MAX(words.learned_from_practice, excluded.learned_from_practice)
            """,
            (
                user_id,
                card["word"],
                normalized,
                card["translation"],
                card["phrase_en"],
                card["phrase_ru"],
                now_iso(),
                learned_from_practice,
            ),
        )


def find_saved_word(user_id, word):
    normalized = normalize_word(word)
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM words
            WHERE user_id = ? AND normalized_word = ?
            LIMIT 1
            """,
            (user_id, normalized),
        ).fetchone()
    return dict(row) if row else None


def list_words_message(user_id):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT word, translation FROM words WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
            (user_id,),
        ).fetchall()
    if not rows:
        return "\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0441\u043b\u043e\u0432. \u041f\u0440\u043e\u0441\u0442\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u044c \u043f\u0435\u0440\u0432\u043e\u0435 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u043e\u0435 \u0441\u043b\u043e\u0432\u043e."

    body = "\n".join(f"- {escape(row['word'])} - {escape(row['translation'])}" for row in rows)
    return f"<b>\u0428\u0430\u0440\u0438\u0448\u044c \u0432 \u044d\u0442\u0438\u0445 \u0441\u043b\u043e\u0432\u0430\u0445:</b>\n{body}"


def format_card(card, label=None):
    title = escape(card["word"]).capitalize()
    if label:
        title = f"{escape(label)} · {title}"
    emoji = escape(choose_context_emoji(card))
    usage_note = escape(
        card.get("usage_note")
        or "\u0423\u043f\u043e\u0442\u0440\u0435\u0431\u043b\u044f\u044e\u0442 \u0432 \u0436\u0438\u0432\u043e\u0439 \u0440\u0435\u0447\u0438, \u043a\u043e\u0433\u0434\u0430 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 \u0432\u0430\u0436\u043d\u0435\u0435 \u0441\u0443\u0445\u043e\u0433\u043e \u043f\u0435\u0440\u0435\u0432\u043e\u0434\u0430."
    )
    return (
        f"{emoji} <b>{title}</b>\n\n"
        f"{escape(card['translation'])}\n\n"
        f"\U0001f4ac \"{escape(card['phrase_en'])}\"\n\n"
        f"- {escape(card['phrase_ru'])}\n\n"
        f"<b>\u0413\u0434\u0435 \u0432\u0441\u0442\u0440\u0435\u0447\u0430\u0435\u0442\u0441\u044f:</b>\n"
        f"{usage_note}"
    )


def get_practice_scenario(scenario_id):
    for scenario in PRACTICE_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    return None


def pick_practice_scenario(level, previous_id=None):
    choices = [
        scenario
        for scenario in PRACTICE_SCENARIOS
        if scenario["level"] == level and scenario["id"] != previous_id
    ]
    if not choices:
        choices = [scenario for scenario in PRACTICE_SCENARIOS if scenario["level"] == level]
    return random.choice(choices or PRACTICE_SCENARIOS)


def send_practice_scenario(chat_id, user_id):
    state = get_user_practice_state(user_id)
    level = min(max(int(state.get("practice_level") or 1), 1), 4)
    previous_id = state.get("current_practice_scenario")
    scenario = pick_practice_scenario(level, previous_id)
    set_practice_state(user_id, True, scenario["id"])
    vocab_line = " · ".join(item["word"] for item in scenario.get("vocab", [])[:3])
    send_message(
        chat_id,
        f"<b>Practice · Level {level}</b>\n\n"
        f"<b>Situation:</b>\n"
        f"{escape(scenario['situation'])}\n\n"
        f"<b>Useful words:</b>\n"
        f"{escape(vocab_line)}\n\n"
        f"Write your answer \U0001f447",
        reply_markup=practice_vocab_keyboard(scenario),
    )
    send_message(chat_id, "Use the word buttons if you want a quick hint.", reply_markup=practice_keyboard())


def practice_feedback_message(answer, scenario):
    normalized = normalize_word(answer)
    answer_words = set(re.findall(r"[a-z]+", normalized))
    keyword_hits = sum(1 for keyword in scenario["keywords"] if keyword in normalized)
    natural_words = set(re.findall(r"[a-z]+", scenario["natural"].lower()))
    answer_overlap = len(answer_words & natural_words)
    is_good = keyword_hits >= 2 or answer_overlap >= 2
    is_almost = keyword_hits == 1 or answer_overlap == 1

    if is_good:
        lead = random.choice(PRACTICE_POSITIVE_REACTIONS)
        fix_label = "More natural:"
    elif is_almost:
        lead = random.choice(PRACTICE_POSITIVE_REACTIONS)
        fix_label = "Tiny fix:"
    else:
        lead = "\u0412\u0438\u0436\u0443 \u0438\u0434\u0435\u044e, \u043d\u043e \u0434\u043b\u044f \u044d\u0442\u043e\u0439 \u0441\u0438\u0442\u0443\u0430\u0446\u0438\u0438 \u0437\u0432\u0443\u0447\u0430\u043b\u043e \u0431\u044b \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u0435\u0435 \u0442\u0430\u043a:"
        fix_label = "Try this:"

    message = (
        f"{lead}\n\n"
        f"{fix_label}\n"
        f"'{escape(scenario['natural'])}'\n\n"
        f"Even better:\n"
        f"'{escape(scenario['better'])}'\n\n"
        f"Why:\n"
        f"{escape(scenario['why'])}\n\n"
        f"Want another one?"
    )
    return message, is_good


def handle_practice_answer(chat_id, user_id, text):
    state = get_user_practice_state(user_id)
    scenario = get_practice_scenario(state.get("current_practice_scenario"))
    if not scenario:
        send_practice_scenario(chat_id, user_id)
        return

    feedback, is_good = practice_feedback_message(text, scenario)
    record_practice_result(user_id, is_good)
    send_message(chat_id, feedback, reply_markup=practice_keyboard())


def answer_callback_query(callback_id):
    if os.getenv("LOCAL_TEST") == "1":
        print(f"\nBOT CALLBACK OK -> {callback_id}\n")
        return {"ok": True}
    return telegram_request("answerCallbackQuery", {"callback_query_id": callback_id})


def save_practice_vocab(user_id, vocab):
    word = vocab["word"]
    save_word(
        user_id,
        {
            "word": word,
            "translation": vocab["translation"],
            "phrase_en": vocab["example"],
            "phrase_ru": "",
            "learned_from_practice": True,
        },
    )


def handle_callback_query(callback_query):
    callback_id = callback_query.get("id")
    data = callback_query.get("data") or ""
    user_id = (callback_query.get("from") or {}).get("id")
    message = callback_query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if callback_id:
        answer_callback_query(callback_id)
    if not user_id or not chat_id or not data.startswith("pv:"):
        return

    try:
        _, scenario_id, raw_index = data.split(":", 2)
    except ValueError:
        return
    scenario = get_practice_scenario(scenario_id)
    if not scenario:
        return
    try:
        vocab = scenario.get("vocab", [])[int(raw_index)]
    except (ValueError, IndexError):
        return

    save_practice_vocab(user_id, vocab)
    send_message(
        chat_id,
        f"<b>{escape(vocab['word'])}</b> = {escape(vocab['translation'])}\n\n"
        f"Example:\n"
        f"\"{escape(vocab['example'])}\"",
        reply_markup=practice_keyboard(),
    )


def get_random_word_for_user(user_id):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM words
            WHERE user_id = ?
            ORDER BY times_sent ASC, RANDOM()
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def mark_word_sent(word_id):
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE words
            SET last_sent_at = ?, times_sent = times_sent + 1
            WHERE id = ?
            """,
            (now_iso(), word_id),
        )


def should_send_reminder(user_id, slot_date, slot_time):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM reminder_log
            WHERE user_id = ? AND slot_date = ? AND slot_time = ?
            """,
            (user_id, slot_date, slot_time),
        ).fetchone()
    return row is None


def mark_reminder_sent(user_id, slot_date, slot_time):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO reminder_log(user_id, slot_date, slot_time, sent_at)
            VALUES(?, ?, ?, ?)
            """,
            (user_id, slot_date, slot_time, now_iso()),
        )


def read_word_of_day():
    if not os.path.exists(WORD_OF_DAY_PATH):
        return ""

    with open(WORD_OF_DAY_PATH, "r", encoding="utf-8") as word_file:
        for raw_line in word_file:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                return line
    return ""


def should_send_word_of_day(user_id, slot_date):
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM word_of_day_log
            WHERE user_id = ? AND slot_date = ?
            """,
            (user_id, slot_date),
        ).fetchone()
    return row is None


def mark_word_of_day_sent(user_id, slot_date):
    with db_connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO word_of_day_log(user_id, slot_date, sent_at)
            VALUES(?, ?, ?)
            """,
            (user_id, slot_date, now_iso()),
        )


def due_slot(timezone):
    current = user_local_now(timezone).strftime("%H:%M")
    return current if current in REMINDER_TIMES else None


def send_due_reminders():
    with db_connect() as conn:
        users = conn.execute("SELECT user_id, chat_id, timezone FROM users").fetchall()

    for user in users:
        user_id = user["user_id"]
        timezone = user["timezone"] or DEFAULT_TIMEZONE
        slot_time = due_slot(timezone)
        if not slot_time:
            continue

        slot_date = user_local_now(timezone).date().isoformat()
        if not should_send_reminder(user_id, slot_date, slot_time):
            continue

        word = get_random_word_for_user(user_id)
        if not word:
            mark_reminder_sent(user_id, slot_date, slot_time)
            continue

        fresh_card = build_word_card(word["word"])
        fresh_card["translation"] = fresh_card["translation"] or word["translation"]
        try:
            send_message(user["chat_id"], format_card(fresh_card))
            mark_word_sent(word["id"])
            mark_reminder_sent(user_id, slot_date, slot_time)
        except Exception as exc:
            print(f"Failed to send reminder to {user_id}: {exc}")


def send_due_word_of_day():
    word = read_word_of_day()
    if not word:
        return

    with db_connect() as conn:
        users = conn.execute("SELECT user_id, chat_id, timezone FROM users").fetchall()

    for user in users:
        user_id = user["user_id"]
        timezone = user["timezone"] or DEFAULT_TIMEZONE
        local_now = user_local_now(timezone)
        if local_now.strftime("%H:%M") != WORD_OF_DAY_TIME:
            continue

        slot_date = local_now.date().isoformat()
        if not should_send_word_of_day(user_id, slot_date):
            continue

        card = build_word_card(word)
        try:
            send_message(
                user["chat_id"],
                format_card(card, label="\u0421\u043b\u043e\u0432\u043e \u0434\u043d\u044f"),
            )
            mark_word_of_day_sent(user_id, slot_date)
        except Exception as exc:
            print(f"Failed to send word of day to {user_id}: {exc}")


def handle_message(message):
    chat = message.get("chat", {})
    user = message.get("from", {})
    chat_id = chat.get("id")
    user_id = user.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not user_id or not text:
        return

    remember_user(user_id, chat_id)

    if text.startswith("/start"):
        set_practice_state(user_id, False)
        send_message(
            chat_id,
            "\u041f\u0440\u0438\u0432\u0435\u0442! \u041e\u0442\u043f\u0440\u0430\u0432\u044c \u043c\u043d\u0435 \u0430\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u043e\u0435 \u0441\u043b\u043e\u0432\u043e \u0438\u043b\u0438 \u0444\u0440\u0430\u0437\u0443, \u0430 \u044f \u0441\u043e\u0445\u0440\u0430\u043d\u044e \u0435\u0435 \u0438 \u0431\u0443\u0434\u0443 \u043f\u0440\u0438\u0441\u044b\u043b\u0430\u0442\u044c \u0432 09:00, 15:00 \u0438 21:00 \u043f\u043e \u0442\u0432\u043e\u0435\u043c\u0443 \u0432\u0440\u0435\u043c\u0435\u043d\u0438.\n\n\u041d\u0430\u0436\u043c\u0438 \u00ab\u0428\u0430\u0440\u044e\u00bb, \u0447\u0442\u043e\u0431\u044b \u0443\u0432\u0438\u0434\u0435\u0442\u044c \u0441\u0432\u043e\u0438 \u0441\u043b\u043e\u0432\u0430, \u0438\u043b\u0438 Practice, \u0447\u0442\u043e\u0431\u044b \u043f\u043e\u0442\u0440\u0435\u043d\u0438\u0442\u044c \u0436\u0438\u0432\u044b\u0435 \u0444\u0440\u0430\u0437\u044b.\n\u0427\u0430\u0441\u043e\u0432\u043e\u0439 \u043f\u043e\u044f\u0441: /tz Europe/Moscow",
        )
        return

    if text.startswith("/words") or text == "\u0428\u0430\u0440\u044e":
        send_message(chat_id, list_words_message(user_id))
        return

    if text.startswith("/help"):
        send_message(chat_id, "\u041a\u043d\u043e\u043f\u043a\u0430 \u00ab\u0428\u0430\u0440\u044e\u00bb - \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u043b\u043e\u0432.\n/tz Europe/Moscow - \u0447\u0430\u0441\u043e\u0432\u043e\u0439 \u043f\u043e\u044f\u0441.\n\n\u0427\u0442\u043e\u0431\u044b \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043b\u043e\u0432\u043e, \u043f\u0440\u043e\u0441\u0442\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u044c \u0435\u0433\u043e.")
        return

    if text.startswith("/tz"):
        parts = text.split(maxsplit=1)
        if len(parts) == 1:
            send_message(chat_id, "\u0423\u043a\u0430\u0436\u0438 \u0447\u0430\u0441\u043e\u0432\u043e\u0439 \u043f\u043e\u044f\u0441, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: /tz Europe/Moscow")
            return
        timezone = parts[1].strip()
        if not valid_timezone(timezone):
            send_message(chat_id, "\u041d\u0435 \u043d\u0430\u0448\u0435\u043b \u0442\u0430\u043a\u043e\u0439 \u0447\u0430\u0441\u043e\u0432\u043e\u0439 \u043f\u043e\u044f\u0441. \u041f\u0440\u0438\u043c\u0435\u0440\u044b: Europe/Moscow, Europe/London, Asia/Dubai, America/New_York.")
            return
        set_user_timezone(user_id, timezone)
        local_time = user_local_now(timezone).strftime("%H:%M")
        send_message(chat_id, f"\u0413\u043e\u0442\u043e\u0432\u043e. \u0422\u0432\u043e\u0439 \u0447\u0430\u0441\u043e\u0432\u043e\u0439 \u043f\u043e\u044f\u0441: {escape(timezone)}. \u0421\u0435\u0439\u0447\u0430\u0441 \u0443 \u0442\u0435\u0431\u044f {local_time}.")
        return

    if text == PRACTICE_BUTTON or text == NEXT_PRACTICE_BUTTON:
        send_practice_scenario(chat_id, user_id)
        return

    if text == BACK_TO_MENU_BUTTON:
        set_practice_state(user_id, False)
        send_message(chat_id, "\u0412\u0435\u0440\u043d\u0443\u043b\u0438\u0441\u044c \u0432 \u043c\u0435\u043d\u044e. \u041a\u0438\u0434\u0430\u0439 \u0441\u043b\u043e\u0432\u043e \u0438\u043b\u0438 \u0436\u043c\u0438 Practice.")
        return

    if contains_cyrillic(text):
        send_cyrillic_meme_reaction(chat_id)
        return

    if get_user_practice_state(user_id).get("practice_mode"):
        handle_practice_answer(chat_id, user_id, text)
        return

    if not is_valid_english_input(text):
        send_message(chat_id, INVALID_ENGLISH_MESSAGE)
        return

    saved_word = find_saved_word(user_id, text)
    if saved_word:
        card = build_word_card(saved_word["word"])
        if not card.get("is_valid_english", True):
            send_message(chat_id, INVALID_ENGLISH_MESSAGE)
            return
        card["translation"] = card["translation"] or saved_word["translation"]
        send_message(
            chat_id,
            "\u0422\u0430\u043a\u043e\u0435 \u0442\u044b \u0443\u0436\u0435 \u0437\u043d\u0430\u0435\u0448\u044c\n\n" + format_card(card),
        )
        return

    card = build_word_card(text)
    if not card.get("is_valid_english", True):
        send_message(chat_id, INVALID_ENGLISH_MESSAGE)
        return
    save_word(user_id, card)
    send_message(chat_id, format_card(card))


def poll_updates():
    offset = 0
    print("BOOT: polling loop started", flush=True)
    while True:
        send_due_reminders()
        send_due_word_of_day()
        try:
            updates = telegram_request("getUpdates", {"timeout": 25, "offset": offset})
            for update in updates:
                offset = max(offset, update["update_id"] + 1)
                if "message" in update:
                    handle_message(update["message"])
                if "callback_query" in update:
                    handle_callback_query(update["callback_query"])
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"Polling error: {exc}")
            time.sleep(5)


def print_runtime_status():
    print(f"Loaded .env from: {app_path('.env')}")
    print(f"Telegram token: {'ok' if TELEGRAM_TOKEN else 'missing'}")
    print(f"OpenRouter key: {'ok' if OPENROUTER_API_KEY else 'missing'}")
    print(f"OpenRouter model: {OPENROUTER_MODEL}")
    print(f"OpenRouter API URL: {OPENROUTER_API_URL}")
    print(f"OpenRouter timeout: {OPENROUTER_TIMEOUT}")
    print(f"Database: {DB_PATH}")


def run_local_test():
    init_db()
    print_runtime_status()
    chat_id = int(os.getenv("LOCAL_TEST_CHAT_ID", "1"))
    user_id = int(os.getenv("LOCAL_TEST_USER_ID", "1"))
    samples = ["/start", "overthinking", "overthinking", "\u0428\u0430\u0440\u044e", "/tz +03:00"]

    for text in samples:
        print(f"\nUSER -> {text}")
        handle_message(
            {
                "chat": {"id": chat_id},
                "from": {"id": user_id},
                "text": text,
            }
        )


if __name__ == "__main__":
    if os.getenv("LOCAL_TEST") == "1":
        run_local_test()
        raise SystemExit

    init_db()
    print("English Telegram bot is running...")
    print_runtime_status()
    poll_updates()
