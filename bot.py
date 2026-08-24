import os
import re
import hmac
import hashlib
import time
import sqlite3
import secrets
import json
import asyncio
from urllib import request
from collections import defaultdict, deque
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
    WebAppInfo,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
    TypeHandler,
    InlineQueryHandler,
)

load_dotenv()

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")).strip()
PROJECT_NAME = os.getenv("PROJECT_NAME", "SpaceNovaX").strip()
TOKEN_SYMBOL = os.getenv("TOKEN_SYMBOL", "SPNX").strip()
OFFICIAL_WEBSITE = os.getenv("OFFICIAL_WEBSITE", "https://spacenovax.com").strip()
OFFICIAL_CHANNEL = os.getenv("OFFICIAL_CHANNEL", "@spacenovaxteam").strip()
OFFICIAL_GROUP = os.getenv("OFFICIAL_GROUP", "@spacesnovax").strip()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://app.spacenovax.com").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "SpaceNovaXAdminBot").strip().lstrip("@")
COMMUNITY_GUIDE_URL = os.getenv(
    "COMMUNITY_GUIDE_URL", f"{OFFICIAL_WEBSITE.rstrip('/')}/getting-started.html"
).strip()
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", "3"))
WARNING_EXPIRY_DAYS = int(os.getenv("WARNING_EXPIRY_DAYS", "30"))
MESSAGE_WINDOW_SECONDS = int(os.getenv("MESSAGE_WINDOW_SECONDS", "10"))
MAX_MESSAGES_PER_WINDOW = int(os.getenv("MAX_MESSAGES_PER_WINDOW", "6"))
AUTO_MUTE_SECONDS = int(os.getenv("AUTO_MUTE_SECONDS", "600"))
JOIN_VERIFICATION_ENABLED = os.getenv("JOIN_VERIFICATION_ENABLED", "true").lower() == "true"
VERIFICATION_TTL_MINUTES = int(os.getenv("VERIFICATION_TTL_MINUTES", "30"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", RENDER_EXTERNAL_URL).strip().rstrip("/")

# NOVA uses Gemini's free tier when a Gemini API key is present in Render.
# Never commit this key to GitHub.
NOVA_GEMINI_API_KEY = (
    os.getenv("NOVA_GEMINI_API_KEY", "").strip()
    or os.getenv("GEMINI_API_KEY", "").strip()
)
NOVA_GEMINI_MODEL = (
    os.getenv("NOVA_GEMINI_MODEL", "").strip()
    or os.getenv("GEMINI_MODEL", "").strip()
    or "gemini-2.5-flash-lite"
)
GUEST_USER_LIMIT_PER_DAY = int(os.getenv("GUEST_USER_LIMIT_PER_DAY", "3"))
GUEST_CHAT_LIMIT_PER_MINUTE = int(os.getenv("GUEST_CHAT_LIMIT_PER_MINUTE", "1"))

LANGUAGES = {
    "ko": ("🇰🇷 한국어", "한국어"), "en": ("🇺🇸 English", "English"),
    "ja": ("🇯🇵 日本語", "日本語"), "zh": ("🇨🇳 中文", "中文"),
    "vi": ("🇻🇳 Tiếng Việt", "Tiếng Việt"), "es": ("🇪🇸 Español", "Español"),
    "pt": ("🇧🇷 Português", "Português"), "ru": ("🇷🇺 Русский", "Русский"),
    "hi": ("🇮🇳 हिन्दी", "हिन्दी"), "tr": ("🇹🇷 Türkçe", "Türkçe"),
    "id": ("🇮🇩 Indonesia", "Indonesia"), "ar": ("🇸🇦 العربية", "العربية"),
}

I18N = {
 "ko": {"welcome":"🚀 SpaceNovaX 공식 봇에 오신 것을 환영합니다.","pin":"📌 이 대화를 텔레그램 상단에 고정해 주세요. 공지, 채굴 상태 및 중요 알림을 빠르게 확인할 수 있습니다.","ref":"🎖 추천 코드가 안전하게 연결되었습니다: {code}","choose":"아래에서 필요한 기능을 선택하세요.","app":"🚀 SpaceNovaX 앱 실행","channel":"📢 공식 채널","group":"💬 공식 그룹","site":"🌐 공식 웹사이트","mining":"⛏ 채굴 안내","mission":"🎯 미션 안내","referral":"👥 추천 안내","lang":"🌐 언어 변경"},
 "en": {"welcome":"🚀 Welcome to the official SpaceNovaX bot.","pin":"📌 Please pin this chat to the top of Telegram for announcements, mining status and important alerts.","ref":"🎖 Referral code linked securely: {code}","choose":"Choose a service below.","app":"🚀 Launch SpaceNovaX","channel":"📢 Official Channel","group":"💬 Official Group","site":"🌐 Official Website","mining":"⛏ Mining Guide","mission":"🎯 Mission Guide","referral":"👥 Referral Guide","lang":"🌐 Change Language"},
 "ja": {"welcome":"🚀 SpaceNovaX公式ボットへようこそ。","pin":"📌 お知らせと重要な通知のため、このチャットをTelegram上部に固定してください。","ref":"🎖 紹介コードを連携しました: {code}","choose":"機能を選択してください。","app":"🚀 アプリを起動","channel":"📢 公式チャンネル","group":"💬 公式グループ","site":"🌐 公式サイト","mining":"⛏ マイニング案内","mission":"🎯 ミッション案内","referral":"👥 紹介案内","lang":"🌐 言語変更"},
 "zh": {"welcome":"🚀 欢迎使用SpaceNovaX官方机器人。","pin":"📌 请将此聊天置顶，以便接收公告、挖矿状态和重要提醒。","ref":"🎖 推荐码已安全绑定：{code}","choose":"请选择服务。","app":"🚀 启动SpaceNovaX","channel":"📢 官方频道","group":"💬 官方群组","site":"🌐 官方网站","mining":"⛏ 挖矿指南","mission":"🎯 任务指南","referral":"👥 推荐指南","lang":"🌐 更改语言"},
 "vi": {"welcome":"🚀 Chào mừng đến bot SpaceNovaX chính thức.","pin":"📌 Hãy ghim cuộc trò chuyện này để nhận thông báo và trạng thái khai thác.","ref":"🎖 Đã liên kết mã giới thiệu: {code}","choose":"Chọn dịch vụ bên dưới.","app":"🚀 Mở SpaceNovaX","channel":"📢 Kênh chính thức","group":"💬 Nhóm chính thức","site":"🌐 Trang web","mining":"⛏ Hướng dẫn đào","mission":"🎯 Nhiệm vụ","referral":"👥 Giới thiệu","lang":"🌐 Đổi ngôn ngữ"},
 "es": {"welcome":"🚀 Bienvenido al bot oficial de SpaceNovaX.","pin":"📌 Fija este chat para recibir anuncios y alertas importantes.","ref":"🎖 Código de referido vinculado: {code}","choose":"Elige un servicio.","app":"🚀 Abrir SpaceNovaX","channel":"📢 Canal oficial","group":"💬 Grupo oficial","site":"🌐 Sitio oficial","mining":"⛏ Guía de minería","mission":"🎯 Misiones","referral":"👥 Referidos","lang":"🌐 Cambiar idioma"},
 "pt": {"welcome":"🚀 Bem-vindo ao bot oficial SpaceNovaX.","pin":"📌 Fixe esta conversa para receber anúncios e alertas.","ref":"🎖 Código de indicação vinculado: {code}","choose":"Escolha um serviço.","app":"🚀 Abrir SpaceNovaX","channel":"📢 Canal oficial","group":"💬 Grupo oficial","site":"🌐 Site oficial","mining":"⛏ Guia de mineração","mission":"🎯 Missões","referral":"👥 Indicações","lang":"🌐 Alterar idioma"},
 "ru": {"welcome":"🚀 Добро пожаловать в официальный бот SpaceNovaX.","pin":"📌 Закрепите чат для уведомлений и статуса майнинга.","ref":"🎖 Реферальный код привязан: {code}","choose":"Выберите функцию.","app":"🚀 Открыть SpaceNovaX","channel":"📢 Официальный канал","group":"💬 Официальная группа","site":"🌐 Официальный сайт","mining":"⛏ Майнинг","mission":"🎯 Миссии","referral":"👥 Рефералы","lang":"🌐 Сменить язык"},
 "hi": {"welcome":"🚀 आधिकारिक SpaceNovaX बॉट में आपका स्वागत है।","pin":"📌 घोषणाओं और अलर्ट के लिए इस चैट को पिन करें।","ref":"🎖 रेफरल कोड जुड़ गया: {code}","choose":"नीचे सेवा चुनें।","app":"🚀 SpaceNovaX खोलें","channel":"📢 आधिकारिक चैनल","group":"💬 आधिकारिक समूह","site":"🌐 वेबसाइट","mining":"⛏ माइनिंग गाइड","mission":"🎯 मिशन","referral":"👥 रेफरल","lang":"🌐 भाषा बदलें"},
 "tr": {"welcome":"🚀 Resmi SpaceNovaX botuna hoş geldiniz.","pin":"📌 Duyuru ve uyarılar için bu sohbeti sabitleyin.","ref":"🎖 Referans kodu bağlandı: {code}","choose":"Bir hizmet seçin.","app":"🚀 SpaceNovaX'i Aç","channel":"📢 Resmi Kanal","group":"💬 Resmi Grup","site":"🌐 Resmi Site","mining":"⛏ Madencilik","mission":"🎯 Görevler","referral":"👥 Referans","lang":"🌐 Dil Değiştir"},
 "id": {"welcome":"🚀 Selamat datang di bot resmi SpaceNovaX.","pin":"📌 Sematkan chat ini untuk pengumuman dan status mining.","ref":"🎖 Kode referral tertaut: {code}","choose":"Pilih layanan.","app":"🚀 Buka SpaceNovaX","channel":"📢 Kanal Resmi","group":"💬 Grup Resmi","site":"🌐 Situs Resmi","mining":"⛏ Panduan Mining","mission":"🎯 Misi","referral":"👥 Referral","lang":"🌐 Ganti Bahasa"},
 "ar": {"welcome":"🚀 مرحبًا بك في بوت SpaceNovaX الرسمي.","pin":"📌 ثبّت هذه المحادثة لتلقي الإعلانات والتنبيهات.","ref":"🎖 تم ربط رمز الإحالة: {code}","choose":"اختر خدمة.","app":"🚀 فتح SpaceNovaX","channel":"📢 القناة الرسمية","group":"💬 المجموعة الرسمية","site":"🌐 الموقع الرسمي","mining":"⛏ دليل التعدين","mission":"🎯 المهام","referral":"👥 الإحالات","lang":"🌐 تغيير اللغة"},
}

ADMIN_IDS = {
    int(item.strip())
    for item in os.getenv("ADMIN_IDS", "").split(",")
    if item.strip().isdigit()
}

DB_PATH = Path(os.getenv("DB_PATH", "spacenovax_bot.db"))
LINK_RE = re.compile(r"(?:https?://|www\.|t\.me/|telegram\.me/|bit\.ly/|tinyurl\.com/|discord\.gg/)[^\s<>()]+", re.I)

BANNED_WORDS = [
    "send private key", "seed phrase", "free usdt", "double your money",
    "admin dm", "support dm", "private key", "guaranteed profit",
    "개인키", "시드구문", "무료 usdt", "관리자 dm", "고수익 보장", "원금 보장",
]
EXTRA_BANNED_WORDS = [
    word.strip().lower() for word in os.getenv("EXTRA_BANNED_WORDS", "").split(",") if word.strip()
]
PROFANITY_WORDS = [
    # A conservative multi-language baseline. Administrators can extend this
    # through EXTRA_BANNED_WORDS without publishing moderation terms in code.
    "fuck", "shit", "bitch", "asshole", "motherfucker", "개새끼", "씨발", "병신", "좆",
    "くそ", "死ね", "混蛋", "傻逼", "puta", "mierda", "пизда", "сука", "orospu", "siktir",
]
ALLOWED_LINK_PREFIXES = [
    item.strip().lower().rstrip("/")
    for item in os.getenv("ALLOWED_LINK_PREFIXES", "").split(",") if item.strip()
] or [
    OFFICIAL_WEBSITE.lower().rstrip("/"),
    "https://app.spacenovax.com",
    f"https://t.me/{BOT_USERNAME.lower()}",
    f"https://t.me/{OFFICIAL_CHANNEL.replace('@', '').lower()}",
    f"https://t.me/{OFFICIAL_GROUP.replace('@', '').lower()}",
    "https://discord.gg/u37axpnfwc",
]
MESSAGE_TIMESTAMPS = defaultdict(deque)
# In-memory only: Guest NOVA stores no question content or chat history.
GUEST_USER_TIMESTAMPS = defaultdict(deque)
GUEST_CHAT_TIMESTAMPS = defaultdict(deque)

PROJECT_KEYWORDS = {
    "website": f"🌐 Official Website: {OFFICIAL_WEBSITE}",
    "homepage": f"🌐 Official Website: {OFFICIAL_WEBSITE}",
    "channel": f"📢 Official Channel: {OFFICIAL_CHANNEL}",
    "group": f"💬 Official Group: {OFFICIAL_GROUP}",
    "symbol": f"🪙 Token Symbol: {TOKEN_SYMBOL}",
    "token": f"🪙 SpaceNovaX Token Symbol: {TOKEN_SYMBOL}",
    "웹사이트": f"🌐 공식 웹사이트: {OFFICIAL_WEBSITE}",
    "홈페이지": f"🌐 공식 웹사이트: {OFFICIAL_WEBSITE}",
    "채널": f"📢 공식 채널: {OFFICIAL_CHANNEL}",
    "그룹": f"💬 공식 그룹: {OFFICIAL_GROUP}",
    "심볼": f"🪙 토큰 심볼: {TOKEN_SYMBOL}",
}

# This guidance is intentionally delivered in a private bot chat. Telegram
# bots cannot proactively DM a member who has never started the bot, and a
# language callback in a group would edit one shared message for everyone.
# The group welcome therefore opens this per-user flow through a deep link.
ONBOARDING = {
    "ko": "🪪 채굴, 미션 및 월드 채팅을 이용하려면 Captain ID가 필요합니다. 아래에서 SpaceNovaX Mini App을 열고 Captain ID를 연결해 주세요.",
    "en": "🪪 Captain ID is required for mining, missions and World Chat. Open the SpaceNovaX Mini App below and connect your Captain ID.",
    "ja": "🪪 マイニング、ミッション、ワールドチャットにはCaptain IDが必要です。下のSpaceNovaX Mini Appを開いてCaptain IDを連携してください。",
    "zh": "🪪 挖矿、任务和世界聊天需要 Captain ID。请打开下方 SpaceNovaX Mini App 并连接您的 Captain ID。",
    "vi": "🪪 Captain ID là bắt buộc để dùng mining, nhiệm vụ và World Chat. Hãy mở Mini App SpaceNovaX bên dưới và kết nối Captain ID.",
    "es": "🪪 Captain ID es necesario para minería, misiones y World Chat. Abre la Mini App de SpaceNovaX y conecta tu Captain ID.",
    "pt": "🪪 O Captain ID é necessário para mineração, missões e World Chat. Abra a Mini App da SpaceNovaX e conecte seu Captain ID.",
    "ru": "🪪 Captain ID требуется для майнинга, миссий и World Chat. Откройте Mini App SpaceNovaX и подключите Captain ID.",
    "hi": "🪪 माइनिंग, मिशन और वर्ल्ड चैट के लिए Captain ID आवश्यक है। नीचे SpaceNovaX Mini App खोलें और अपना Captain ID कनेक्ट करें।",
    "tr": "🪪 Madencilik, görevler ve World Chat için Captain ID gereklidir. Aşağıdaki SpaceNovaX Mini App'i açın ve Captain ID'nizi bağlayın.",
    "id": "🪪 Captain ID diperlukan untuk mining, misi, dan World Chat. Buka Mini App SpaceNovaX di bawah lalu hubungkan Captain ID Anda.",
    "ar": "🪪 يلزم Captain ID للتعدين والمهام وWorld Chat. افتح تطبيق SpaceNovaX Mini App أدناه واربط Captain ID الخاص بك.",
}

GROUP_WELCOME = {
    "ko": "🚀 {name}님, SpaceNovaX 월드 커뮤니티에 오신 것을 환영합니다!\n\n채굴·미션·월드 채팅을 시작하려면 아래 버튼으로 봇을 열고 언어를 선택한 뒤 Captain ID를 연결해 주세요.",
    "en": "🚀 Welcome to the SpaceNovaX World Community, {name}!\n\nTo start mining, missions and World Chat, open the bot below, choose your language and connect your Captain ID.",
}


class Database:
    """Small SQLite/PostgreSQL compatibility layer for the existing bot SQL."""

    def __init__(self):
        self.is_postgres = bool(DATABASE_URL)
        if self.is_postgres:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("DATABASE_URL requires psycopg. Install requirements.txt first.") from exc
            self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row

    def execute(self, query, params=()):
        if self.is_postgres:
            query = query.replace("?", "%s")
        return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def db():
    conn = Database()
    user_id_type = "BIGINT" if conn.is_postgres else "INTEGER"
    log_id = "BIGSERIAL PRIMARY KEY" if conn.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id {user_id_type} PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            language TEXT DEFAULT 'en',
            referral_code TEXT,
            referred_by TEXT
        )
    """)
    if conn.is_postgres:
        for column, definition in (("language", "TEXT DEFAULT 'en'"), ("referral_code", "TEXT"), ("referred_by", "TEXT")):
            conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {definition}")
    else:
        for column, definition in (("language", "TEXT DEFAULT 'en'"), ("referral_code", "TEXT"), ("referred_by", "TEXT")):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id BIGINT,
            user_id BIGINT,
            count INTEGER DEFAULT 0,
            updated_at TEXT,
            PRIMARY KEY(chat_id, user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id %s,
            chat_id BIGINT,
            user_id BIGINT,
            action TEXT,
            detail TEXT,
            created_at TEXT
        )
    """ % log_id)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_verifications (
            token TEXT PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id %s,
            chat_id BIGINT NOT NULL,
            reporter_id BIGINT NOT NULL,
            target_user_id BIGINT,
            message_id BIGINT,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    """ % log_id)
    conn.commit()
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def is_admin(user_id):
    return user_id in ADMIN_IDS


def upsert_user(user):
    if not user:
        return
    conn = db()
    existing = conn.execute(
        "SELECT user_id FROM users WHERE user_id=?", (user.id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (user.username, user.first_name, user.id),
        )
    else:
        conn.execute(
            "INSERT INTO users(user_id, username, first_name, joined_at) VALUES (?, ?, ?, ?)",
            (user.id, user.username, user.first_name, now_iso()),
        )
    conn.commit()
    conn.close()


def stored_referral_code(user_id):
    conn = db()
    row = conn.execute(
        "SELECT referred_by FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return str(row["referred_by"] or "").strip().upper() if row else ""


def stored_language(user_id):
    conn = db()
    row = conn.execute("SELECT language FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["language"] if row and row["language"] in LANGUAGES else "en"


def is_expired(iso_timestamp):
    try:
        return datetime.fromisoformat(iso_timestamp) <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return True


def create_verification(chat_id, user_id):
    token = secrets.token_urlsafe(16)
    left = secrets.randbelow(8) + 1
    right = secrets.randbelow(8) + 1
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TTL_MINUTES)).isoformat()
    conn = db()
    conn.execute("DELETE FROM pending_verifications WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.execute(
        "INSERT INTO pending_verifications(token, chat_id, user_id, question, answer, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (token, chat_id, user_id, f"{left} + {right} = ?", str(left + right), expires_at, now_iso()),
    )
    conn.commit()
    conn.close()
    return token, left, right


def get_verification(token, user_id):
    conn = db()
    row = conn.execute(
        "SELECT token, chat_id, user_id, question, answer, expires_at FROM pending_verifications WHERE token=? AND user_id=?",
        (token, user_id),
    ).fetchone()
    conn.close()
    if not row or is_expired(row["expires_at"]):
        return None
    return row


def consume_verification(token):
    conn = db()
    conn.execute("DELETE FROM pending_verifications WHERE token=?", (token,))
    conn.commit()
    conn.close()


def captcha_keyboard(token, correct):
    choices = [correct, correct + 1, max(0, correct - 1)]
    # Shuffle without a predictable correct position while keeping callback
    # data server-verified against the one-time token.
    secrets.SystemRandom().shuffle(choices)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(choice), callback_data=f"captcha:{token}:{choice}") for choice in choices],
    ])


def has_unapproved_link(text):
    for match in LINK_RE.findall(text or ""):
        url = match.lower().rstrip(".,!?:;)")
        normalized = url if url.startswith("http") else f"https://{url}"
        # Accept only the official destination itself, a path below it, or a query.
        # This avoids look-alike domains such as spacenovax.com.evil.example.
        is_official = any(
            normalized == prefix
            or normalized.startswith(prefix + "/")
            or normalized.startswith(prefix + "?")
            for prefix in ALLOWED_LINK_PREFIXES
        )
        if not is_official:
            return True
    return False


def exceeds_message_rate(chat_id, user_id):
    key = (chat_id, user_id)
    now = time.monotonic()
    timestamps = MESSAGE_TIMESTAMPS[key]
    while timestamps and now - timestamps[0] > MESSAGE_WINDOW_SECONDS:
        timestamps.popleft()
    timestamps.append(now)
    return len(timestamps) > MAX_MESSAGES_PER_WINDOW



def guest_rate_status(user_id, chat_id):
    """Return an optional rate-limit message without persisting guest data."""
    now = time.monotonic()
    user_window = GUEST_USER_TIMESTAMPS[user_id]
    while user_window and now - user_window[0] >= 24 * 60 * 60:
        user_window.popleft()
    if len(user_window) >= GUEST_USER_LIMIT_PER_DAY:
        return "⏳ NOVA Guest limit reached for today (3 requests). Please try again tomorrow or open SpaceNovaX."

    chat_window = GUEST_CHAT_TIMESTAMPS[chat_id]
    while chat_window and now - chat_window[0] >= 60:
        chat_window.popleft()
    if len(chat_window) >= GUEST_CHAT_LIMIT_PER_MINUTE:
        return "⏳ NOVA Guest is cooling down for one minute in this chat. Please try again shortly."

    user_window.append(now)
    chat_window.append(now)
    return ""


def guest_fallback_answer():
    return (
        "⚡ NOVA AI is available inside the SpaceNovaX Mini App.\n\n"
        "Open it to explore community mining, NOVA AI, missions, games and global navigation."
    )


def _json_post(url, payload, headers=None, timeout=18):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _gemini_output(data):
    candidates = data.get("candidates", []) or []
    if not candidates:
        return ""
    content = candidates[0].get("content", {}) if isinstance(candidates[0], dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    return "".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict)
    ).strip()


async def nova_answer(question):
    """Generate a concise Gemini-free-tier answer without storing prompts locally."""
    if not NOVA_GEMINI_API_KEY:
        return guest_fallback_answer()

    instructions = (
        "You are NOVA, the concise SpaceNovaX Telegram assistant. "
        "Answer in the user's language when clear. Explain SpaceNovaX basics: community mining, "
        "missions, Captain ID, the Mini App, games, global navigation and community services. "
        "Do not invent token prices, rewards, listings, partnerships, launch dates or account data. "
        "Do not request private keys, seed phrases, passwords or personal data. "
        "For financial topics, provide general educational information only and include "
        "'Not financial advice — do your own research.' Keep the reply under 700 characters."
    )
    payload = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 260},
    }
    try:
        response = await asyncio.to_thread(
            _json_post,
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{NOVA_GEMINI_MODEL}:generateContent?key={NOVA_GEMINI_API_KEY}"
            ),
            payload,
            None,
            18,
        )
        answer = _gemini_output(response)
        if answer:
            return answer[:900]
    except Exception as exc:
        # Log only the HTTP status/class; never log API keys or question text.
        status = getattr(exc, "code", "unknown")
        print(f"NOVA Gemini request failed: {type(exc).__name__} ({status})")
    return guest_fallback_answer()


async def answer_guest_query(query_id, text):
    """Use Telegram's official Guest Mode method, absent from PTB 21.6."""
    if not query_id:
        return
    result = {
        "type": "article",
        "id": secrets.token_hex(8),
        "title": "NOVA · SpaceNovaX",
        "input_message_content": {
            "message_text": text[:1000],
            "disable_web_page_preview": True,
        },
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "🚀 Open SpaceNovaX",
                    "url": f"https://t.me/{BOT_USERNAME}?startapp=guest",
                }
            ]]
        },
    }
    try:
        await asyncio.to_thread(
            _json_post,
            f"https://api.telegram.org/bot{BOT_TOKEN}/answerGuestQuery",
            {"guest_query_id": query_id, "result": result},
            None,
            12,
        )
    except Exception:
        # A guest query can only be answered once; failures must not affect
        # normal bot commands or moderation.
        pass


async def guest_nova(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Bot API 10 guest_message updates while keeping PTB 21.6 unchanged."""
    raw = (getattr(update, "api_kwargs", {}) or {}).get("guest_message")
    if not isinstance(raw, dict):
        return

    query_id = str(raw.get("guest_query_id") or "")
    caller = raw.get("guest_bot_caller_user") or raw.get("from") or {}
    caller_chat = raw.get("guest_bot_caller_chat") or raw.get("chat") or {}
    user_id = str(caller.get("id") or "guest")
    chat_id = str(caller_chat.get("id") or user_id)
    question = str(raw.get("text") or raw.get("caption") or "")
    question = re.sub(rf"@{re.escape(BOT_USERNAME)}\b", "", question, flags=re.I).strip(" \t\r\n:,-")
    if not question:
        await answer_guest_query(
            query_id,
            "⚡ Ask NOVA about SpaceNovaX, community mining, missions, Captain ID or the Mini App.",
        )
        return

    limited = guest_rate_status(user_id, chat_id)
    if limited:
        await answer_guest_query(query_id, limited)
        return

    await answer_guest_query(query_id, await nova_answer(question))



def inline_nova_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🚀 Open SpaceNovaX",
            url=f"https://t.me/{BOT_USERNAME}?startapp=inline",
        )
    ]])


def inline_nova_result(title, description, message_text):
    return InlineQueryResultArticle(
        id=secrets.token_hex(8),
        title=title,
        description=re.sub(r"\s+", " ", description).strip()[:180],
        input_message_content=InputTextMessageContent(
            message_text=message_text[:1000],
            disable_web_page_preview=True,
        ),
        reply_markup=inline_nova_keyboard(),
    )


async def inline_nova(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer an explicit inline question without calling AI while the user types."""
    query = update.inline_query
    if not query:
        return

    question = (query.query or "").strip()
    if not question:
        prompt = "⚡ Type a SpaceNovaX question and end it with a question mark (?); NOVA will prepare a shareable answer."
        await query.answer(
            [inline_nova_result("Ask NOVA · SpaceNovaX", prompt, prompt)],
            cache_time=0,
            is_personal=True,
        )
        return

    # Inline updates arrive on every keystroke. A final '?' prevents accidental
    # API calls while a user is still typing their question.
    if not question.endswith("?"):
        prompt = "Finish the question with '?' to ask NOVA. Example: What is SpaceNovaX?"
        await query.answer(
            [inline_nova_result("NOVA is ready", prompt, prompt)],
            cache_time=0,
            is_personal=True,
        )
        return

    limited = guest_rate_status(str(query.from_user.id), f"inline:{query.from_user.id}")
    if limited:
        await query.answer(
            [inline_nova_result("NOVA limit", limited, limited)],
            cache_time=0,
            is_personal=True,
        )
        return

    answer = await nova_answer(question)
    await query.answer(
        [inline_nova_result("NOVA · SpaceNovaX", answer, answer)],
        cache_time=0,
        is_personal=True,
    )


def get_warning_count(chat_id, user_id):
    conn = db()
    row = conn.execute(
        "SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return 0
    try:
        stale = datetime.fromisoformat(row["updated_at"]) < datetime.now(timezone.utc) - timedelta(days=WARNING_EXPIRY_DAYS)
    except (TypeError, ValueError):
        stale = True
    if stale:
        conn.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        conn.commit()
        conn.close()
        return 0
    conn.close()
    return int(row["count"])


def set_warning(chat_id, user_id, count):
    conn = db()
    conn.execute("""
        INSERT INTO warnings(chat_id, user_id, count, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id)
        DO UPDATE SET count=?, updated_at=?
    """, (chat_id, user_id, count, now_iso(), count, now_iso()))
    conn.commit()
    conn.close()


def add_warning(chat_id, user_id):
    count = get_warning_count(chat_id, user_id) + 1
    set_warning(chat_id, user_id, count)
    return count


def remove_warning(chat_id, user_id):
    count = max(0, get_warning_count(chat_id, user_id) - 1)
    set_warning(chat_id, user_id, count)
    return count


def log_action(chat_id, user_id, action, detail=""):
    conn = db()
    conn.execute(
        "INSERT INTO logs(chat_id, user_id, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, user_id, action, detail, now_iso()),
    )
    conn.commit()
    conn.close()


def language_keyboard():
    rows, items = [], list(LANGUAGES.items())

    logs = conn.execute("SELECT COUNT(*) AS c FROM logs").fetchone()["c"]
    conn.close()
    await update.effective_message.reply_text(
        f"📊 {PROJECT_NAME} Bot Status\n\n"
        f"Users: {users}\n"
        f"Warned users: {warned}\n"
        f"Moderation logs: {logs}\n"
        f"Auto-ban threshold: {MAX_WARNINGS}"
    )


async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to a user's message with /warn.")
        return
    target = update.effective_message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    count = add_warning(chat_id, target.id)
    log_action(chat_id, target.id, "manual_warn", f"count={count}")
    await update.effective_message.reply_text(
        f"⚠️ {target.first_name} warning {count}/{MAX_WARNINGS}"
    )
    if count >= MAX_WARNINGS:
        await context.bot.ban_chat_member(chat_id, target.id)
        await update.effective_message.reply_text(f"🚫 {target.first_name} has been banned.")


async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to a user's message with /unwarn.")
        return
    target = update.effective_message.reply_to_message.from_user
    count = remove_warning(update.effective_chat.id, target.id)
    await update.effective_message.reply_text(
        f"✅ {target.first_name}'s warnings are now {count}/{MAX_WARNINGS}."
    )


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to a user's message with /ban.")
        return
    target = update.effective_message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await update.effective_message.reply_text(f"🚫 {target.first_name} has been banned.")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Usage: /unban user_id")
        return
    await context.bot.unban_chat_member(update.effective_chat.id, int(context.args[0]))
    await update.effective_message.reply_text("✅ User has been unbanned.")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to a user's message with /mute.")
        return
    target = update.effective_message.reply_to_message.from_user
    until = datetime.now(timezone.utc) + timedelta(hours=1)
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        target.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    await update.effective_message.reply_text(
        f"🔇 {target.first_name} has been muted for 1 hour."
    )


async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to the message you want to pin with /pin.")
        return
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.reply_to_message.message_id,
    )
    await update.effective_message.reply_text("📌 Message pinned.")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("Reply to the suspicious message with /report.")
        return
    target = msg.reply_to_message.from_user
    detail = " ".join(context.args).strip()[:500]
    conn = db()
    conn.execute(
        "INSERT INTO reports(chat_id, reporter_id, target_user_id, message_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg.chat_id, msg.from_user.id, target.id, msg.reply_to_message.message_id, detail, now_iso()),
    )
    conn.commit()
    conn.close()
    await msg.reply_text("✅ Report received. The moderation team has been notified.")
    notice = (
        f"🚨 {PROJECT_NAME} report\n"
        f"Chat: {msg.chat_id}\nReporter: {msg.from_user.id}\n"
        f"Target: {target.id} (@{target.username or 'no_username'})\n"
        f"Message: {msg.reply_to_message.message_id}\n"
        f"Detail: {detail or 'No additional detail'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, notice)
        except Exception:
            # Telegram cannot message an administrator who has not started the
            # bot; the report remains in the persistent reports table.
            pass


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    old = update.chat_member.old_chat_member.status
    new = update.chat_member.new_chat_member.status
    user = update.chat_member.new_chat_member.user
    if old in ("left", "kicked") and new in ("member", "restricted"):
        upsert_user(user)
        # Keep the group message brief; the private deep link opens a
        # user-specific 12-language screen without changing the group card.
        lang = "en"
        conn = db()
        row = conn.execute("SELECT language FROM users WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        if row and row["language"] in LANGUAGES:
            lang = row["language"]
        template = GROUP_WELCOME.get(lang, GROUP_WELCOME["en"])
        verification_token = ""
        if JOIN_VERIFICATION_ENABLED:
            try:
                verification_token, _, _ = create_verification(update.effective_chat.id, user.id)
                await context.bot.restrict_chat_member(
                    update.effective_chat.id,
                    user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
            except Exception:
                # Do not block a newcomer when the bot lacks the Telegram
                # administrator permission required to restrict members.
                verification_token = ""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=template.format(name=user.first_name),
            reply_markup=group_welcome_keyboard(verification_token),
        )


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    user = msg.from_user
    if not user or user.is_bot:
        return
    chat_id = msg.chat_id
    text = (msg.text or msg.caption or "").lower()
    upsert_user(user)
    if is_admin(user.id):
        return
    for key, response in PROJECT_KEYWORDS.items():
        if key in text:
            await msg.reply_text(response)
            return
    if exceeds_message_rate(chat_id, user.id):
        until = datetime.now(timezone.utc) + timedelta(seconds=AUTO_MUTE_SECONDS)
        try:
            await context.bot.restrict_chat_member(
                chat_id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until,
            )
        except Exception:
            pass
        log_action(chat_id, user.id, "flood_mute", f"seconds={AUTO_MUTE_SECONDS}")
        await context.bot.send_message(
            chat_id, f"🔇 {user.first_name} was muted for {AUTO_MUTE_SECONDS // 60} minutes for message flooding.",
        )
        return
    has_link = has_unapproved_link(text)
    has_bad_word = any(word.lower() in text for word in [*BANNED_WORDS, *EXTRA_BANNED_WORDS, *PROFANITY_WORDS])
    compact = text.replace(" ", "")
    repeated = len(text) > 20 and compact and len(set(compact)) <= 4
    if has_link or has_bad_word or repeated:
        try:
            await msg.delete()
        except Exception:
            pass
        count = add_warning(chat_id, user.id)
        reason = "link" if has_link else "language" if has_bad_word else "repeated_text"
        log_action(chat_id, user.id, "auto_warn", f"reason={reason};count={count}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ {user.first_name}, unsafe or spam message removed. Warning: {count}/{MAX_WARNINGS}",
        )
        if count >= MAX_WARNINGS:
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 {user.first_name} has been banned due to repeated warnings.",
            )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")
    if MINI_APP_URL and not MINI_APP_URL.startswith("https://"):
        raise RuntimeError("MINI_APP_URL must start with https://")
    async def configure_bot(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Open SpaceNovaX / 언어 선택"),
            BotCommand("about", "About SpaceNovaX"),
            BotCommand("rules", "Community rules"),
            BotCommand("stats", "Bot status"),
            BotCommand("help", "Command list"),
            BotCommand("report", "Report a replied message"),
        ])

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(configure_bot).build()
    handlers = [
        ("start", start), ("rules", rules), ("rules_kr", rules_kr),
        ("about", about), ("about_kr", about_kr), ("help", help_cmd),
        ("stats", stats), ("warn", warn), ("unwarn", unwarn),
        ("ban", ban), ("unban", unban), ("mute", mute), ("pin", pin), ("report", report),
    ]
    for cmd, func in handlers:
        app.add_handler(CommandHandler(cmd, func))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(InlineQueryHandler(inline_nova))
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, moderate_message))
    # PTB 21.6 keeps Bot API 10 guest_message in Update.api_kwargs.
    app.add_handler(TypeHandler(Update, guest_nova))
    allowed_updates = list(dict.fromkeys([*Update.ALL_TYPES, "guest_message"]))
    if WEBHOOK_URL:
        print(f"{PROJECT_NAME} community bot is running in webhook mode on port {PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="telegram",
            webhook_url=f"{WEBHOOK_URL}/telegram",
            drop_pending_updates=False,
            allowed_updates=allowed_updates,
        )
    else:
        print(f"{PROJECT_NAME} community bot is running in local polling mode...")
        app.run_polling(drop_pending_updates=False, allowed_updates=allowed_updates)


if __name__ == "__main__":
    main()