import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PROJECT_NAME = os.getenv("PROJECT_NAME", "SpaceNovaX").strip()
TOKEN_SYMBOL = os.getenv("TOKEN_SYMBOL", "SPNX").strip()
OFFICIAL_WEBSITE = os.getenv("OFFICIAL_WEBSITE", "https://spacenovax.com").strip()
OFFICIAL_CHANNEL = os.getenv("OFFICIAL_CHANNEL", "@SpaceNovaX").strip()
OFFICIAL_GROUP = os.getenv("OFFICIAL_GROUP", "@SpaceNovaXGlobal").strip()
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()
MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", "3"))
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", RENDER_EXTERNAL_URL).strip().rstrip("/")

ADMIN_IDS = {
    int(item.strip())
    for item in os.getenv("ADMIN_IDS", "").split(",")
    if item.strip().isdigit()
}

DB_PATH = Path(os.getenv("DB_PATH", "spacenovax_bot.db"))
LINK_RE = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/|bit\.ly|tinyurl|discord\.gg)", re.I
)

BANNED_WORDS = [
    "send private key", "seed phrase", "free usdt", "double your money",
    "admin dm", "support dm", "private key", "guaranteed profit",
    "개인키", "시드구문", "무료 usdt", "관리자 dm", "고수익 보장", "원금 보장",
]

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


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            updated_at TEXT,
            PRIMARY KEY(chat_id, user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            action TEXT,
            detail TEXT,
            created_at TEXT
        )
    """)
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


def get_warning_count(chat_id, user_id):
    conn = db()
    row = conn.execute(
        "SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)
    ).fetchone()
    conn.close()
    return int(row["count"]) if row else 0


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


def main_keyboard():
    keyboard = []
    if MINI_APP_URL:
        keyboard.append([
            InlineKeyboardButton(
                "🚀 Launch SpaceNovaX", web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ])
    keyboard.extend([
        [InlineKeyboardButton("Official Website", url=OFFICIAL_WEBSITE)],
        [InlineKeyboardButton(
            "Official Channel", url=f"https://t.me/{OFFICIAL_CHANNEL.replace('@', '')}"
        )],
        [InlineKeyboardButton(
            "Official Group", url=f"https://t.me/{OFFICIAL_GROUP.replace('@', '')}"
        )],
    ])
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)
    mini_app_line = "🚀 Launch the SpaceNovaX Mini App with the button below.\n\n" if MINI_APP_URL else ""
    await update.effective_message.reply_text(
        f"🚀 Welcome to {PROJECT_NAME}\n\n"
        f"{mini_app_line}"
        "This bot provides official project information and community moderation.\n\n"
        "Commands:\n"
        "/rules - Community rules\n"
        "/about - About SpaceNovaX\n"
        "/rules_kr - 한국어 커뮤니티 규칙\n"
        "/about_kr - 한국어 프로젝트 소개\n"
        "/help - Command list",
        reply_markup=main_keyboard(),
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"📌 {PROJECT_NAME} Community Rules\n\n"
        "1. No scam or phishing links.\n"
        "2. Never ask for private keys or seed phrases.\n"
        "3. No spam, advertising, or abusive language.\n"
        "4. Do not impersonate admins or support staff.\n"
        "5. Always do your own research. Investment decisions are your responsibility.\n\n"
        f"Users who receive {MAX_WARNINGS} warnings may be automatically banned."
    )


async def rules_kr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"📌 {PROJECT_NAME} 커뮤니티 규칙\n\n"
        "1. 사기 링크 및 피싱 링크 금지\n"
        "2. 개인키 또는 시드 구문 요구 금지\n"
        "3. 욕설, 도배 및 광고 금지\n"
        "4. 관리자 또는 고객지원 사칭 금지\n"
        "5. 투자 판단과 책임은 본인에게 있습니다.\n\n"
        f"경고 {MAX_WARNINGS}회 이상이면 자동 차단될 수 있습니다."
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"🚀 Welcome to {PROJECT_NAME}\n\n"
        f"{PROJECT_NAME} is a next-generation Web3 ecosystem focused on community growth, "
        "AI-powered innovation, and space-inspired digital experiences.\n\n"
        f"Token Symbol: {TOKEN_SYMBOL}\n"
        f"Official Website: {OFFICIAL_WEBSITE}\n"
        f"Official Channel: {OFFICIAL_CHANNEL}\n"
        f"Official Group: {OFFICIAL_GROUP}"
    )


async def about_kr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"🚀 {PROJECT_NAME}에 오신 것을 환영합니다.\n\n"
        f"{PROJECT_NAME}는 커뮤니티 성장, AI 혁신, 우주 테마 디지털 경험을 결합한 "
        "차세대 Web3 생태계입니다.\n\n"
        f"토큰 심볼: {TOKEN_SYMBOL}\n"
        f"공식 웹사이트: {OFFICIAL_WEBSITE}\n"
        f"공식 채널: {OFFICIAL_CHANNEL}\n"
        f"공식 그룹: {OFFICIAL_GROUP}"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "SpaceNovaX Bot Commands\n\n"
        "/start - Start bot\n"
        "/rules - Community rules\n"
        "/about - About SpaceNovaX\n"
        "/rules_kr - Korean rules\n"
        "/about_kr - Korean introduction\n"
        "/stats - Bot status\n\n"
        "Admin only:\n"
        "/warn - Warn replied user\n"
        "/unwarn - Remove warning\n"
        "/ban - Ban replied user\n"
        "/unban user_id - Unban user\n"
        "/mute - Mute replied user for 1 hour\n"
        "/pin - Pin replied message"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    warned = conn.execute("SELECT COUNT(*) AS c FROM warnings WHERE count > 0").fetchone()["c"]
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


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    old = update.chat_member.old_chat_member.status
    new = update.chat_member.new_chat_member.status
    user = update.chat_member.new_chat_member.user
    if old in ("left", "kicked") and new in ("member", "restricted"):
        upsert_user(user)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🚀 Welcome {user.first_name} to {PROJECT_NAME}!\n\n"
                "Please read /rules before chatting.\n"
                "한국어 규칙: /rules_kr\n\n"
                f"Website: {OFFICIAL_WEBSITE}"
            ),
        )


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return
    user = msg.from_user
    chat_id = msg.chat_id
    text = msg.text.lower()
    upsert_user(user)
    if is_admin(user.id):
        return
    for key, response in PROJECT_KEYWORDS.items():
        if key in text:
            await msg.reply_text(response)
            return
    has_link = bool(LINK_RE.search(text))
    has_bad_word = any(word.lower() in text for word in BANNED_WORDS)
    compact = text.replace(" ", "")
    repeated = len(text) > 20 and compact and len(set(compact)) <= 4
    if has_link or has_bad_word or repeated:
        try:
            await msg.delete()
        except Exception:
            pass
        count = add_warning(chat_id, user.id)
        log_action(chat_id, user.id, "auto_warn", f"count={count}")
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
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    handlers = [
        ("start", start), ("rules", rules), ("rules_kr", rules_kr),
        ("about", about), ("about_kr", about_kr), ("help", help_cmd),
        ("stats", stats), ("warn", warn), ("unwarn", unwarn),
        ("ban", ban), ("unban", unban), ("mute", mute), ("pin", pin),
    ]
    for cmd, func in handlers:
        app.add_handler(CommandHandler(cmd, func))
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    if WEBHOOK_URL:
        print(f"{PROJECT_NAME} community bot is running in webhook mode on port {PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="telegram",
            webhook_url=f"{WEBHOOK_URL}/telegram",
            drop_pending_updates=False,
        )
    else:
        print(f"{PROJECT_NAME} community bot is running in local polling mode...")
        app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
