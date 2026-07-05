import os
import re
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PROJECT_NAME = os.getenv("PROJECT_NAME", "SpaceNovaX").strip()
POINT_NAME = os.getenv("POINT_NAME", "SNP").strip()
TOKEN_SYMBOL = os.getenv("TOKEN_SYMBOL", "SPNX").strip()

WEBSITE_URL = os.getenv("WEBSITE_URL", "http://www.spacenovax.com").strip()
YOUTUBE_URL = os.getenv("YOUTUBE_URL", "https://youtube.com/@spacenovaxteam").strip()
X_URL = os.getenv("X_URL", "https://x.com/spacenovaxteam").strip()
TELEGRAM_GROUP_URL = os.getenv("TELEGRAM_GROUP_URL", "https://t.me/spacesnovax").strip()
TELEGRAM_CHANNEL_URL = os.getenv("TELEGRAM_CHANNEL_URL", "https://t.me/spacenovaxteam").strip()
DISCORD_URL = os.getenv("DISCORD_URL", "https://discord.gg/rxVNWMC8e8").strip()

MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", "3"))
MINING_REWARD = int(os.getenv("MINING_REWARD", "100"))
MINING_HOURS = int(os.getenv("MINING_HOURS", "24"))

ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

DB_PATH = Path("spacenovax_points_bot.db")

LINK_RE = re.compile(r"(bit\.ly|tinyurl|free-usdt|airdrop-claim|seed phrase|private key|connect wallet now)", re.I)
SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

MISSION_REWARDS = {
    "website": 100,
    "telegram_group": 200,
    "telegram_channel": 200,
    "youtube": 300,
    "x": 300,
    "discord": 300,
}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            points INTEGER DEFAULT 0,
            wallet TEXT,
            referrer_id INTEGER,
            last_mining_at TEXT,
            joined_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            user_id INTEGER,
            mission_key TEXT,
            completed_at TEXT,
            PRIMARY KEY(user_id, mission_key)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
    """)

    conn.commit()
    return conn


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def is_admin(user_id):
    return user_id in ADMIN_IDS


def upsert_user(user, referrer_id=None):
    conn = db()
    existing = conn.execute("SELECT * FROM users WHERE user_id=?", (user.id,)).fetchone()

    if existing:
        conn.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (user.username, user.first_name, user.id))
    else:
        if referrer_id == user.id:
            referrer_id = None

        conn.execute("""
            INSERT INTO users(user_id, username, first_name, points, wallet, referrer_id, last_mining_at, joined_at)
            VALUES (?, ?, ?, ?, NULL, ?, NULL, ?)
        """, (user.id, user.username, user.first_name, 100, referrer_id, now_iso()))

        if referrer_id:
            conn.execute("UPDATE users SET points = points + 500 WHERE user_id=?", (referrer_id,))

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def add_points(user_id, amount):
    conn = db()
    conn.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def complete_mission_once(user_id, mission_key):
    conn = db()
    exists = conn.execute("SELECT * FROM missions WHERE user_id=? AND mission_key=?", (user_id, mission_key)).fetchone()

    if exists:
        conn.close()
        return False

    reward = MISSION_REWARDS.get(mission_key, 0)
    conn.execute("INSERT INTO missions(user_id, mission_key, completed_at) VALUES (?, ?, ?)", (user_id, mission_key, now_iso()))
    conn.execute("UPDATE users SET points = points + ? WHERE user_id=?", (reward, user_id))
    conn.commit()
    conn.close()
    return True


def referral_count(user_id):
    conn = db()
    count = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referrer_id=?", (user_id,)).fetchone()["c"]
    conn.close()
    return count


def get_warning_count(chat_id, user_id):
    conn = db()
    row = conn.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
    conn.close()
    return int(row["count"]) if row else 0


def add_warning(chat_id, user_id):
    count = get_warning_count(chat_id, user_id) + 1
    conn = db()
    conn.execute("""
        INSERT INTO warnings(chat_id, user_id, count)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id)
        DO UPDATE SET count=?
    """, (chat_id, user_id, count, count))
    conn.commit()
    conn.close()
    return count


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer_id = None

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_") and arg.replace("ref_", "").isdigit():
            referrer_id = int(arg.replace("ref_", ""))

    upsert_user(user, referrer_id)

    keyboard = [
        [InlineKeyboardButton("🌐 Website", url=WEBSITE_URL), InlineKeyboardButton("📢 Telegram Channel", url=TELEGRAM_CHANNEL_URL)],
        [InlineKeyboardButton("💬 Telegram Group", url=TELEGRAM_GROUP_URL), InlineKeyboardButton("▶ YouTube", url=YOUTUBE_URL)],
        [InlineKeyboardButton("𝕏 X", url=X_URL), InlineKeyboardButton("🎮 Discord", url=DISCORD_URL)],
    ]

    await update.message.reply_text(
        f"🚀 Welcome to {PROJECT_NAME}\n\n"
        f"Earn {POINT_NAME} by mining, completing missions, and inviting friends.\n\n"
        f"Commands:\n"
        f"/mine - Start daily mining\n"
        f"/mission - Mission list\n"
        f"/points - My points\n"
        f"/ref - Referral link\n"
        f"/rank - Ranking\n"
        f"/wallet - Register Solana wallet\n"
        f"/about - About project\n"
        f"/rules - Rules\n\n"
        f"가입 보상: +100 {POINT_NAME}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚀 {PROJECT_NAME}\n\n"
        f"{PROJECT_NAME} is a Solana-based Web3 project focused on community growth, AI-powered innovation, and space-inspired digital assets.\n\n"
        f"Current phase: Community points mining\n"
        f"Point: {POINT_NAME}\n"
        f"Future token: {TOKEN_SYMBOL}\n"
        f"Network: Solana\n\n"
        f"Website: {WEBSITE_URL}\n"
        f"YouTube: {YOUTUBE_URL}\n"
        f"X: {X_URL}\n"
        f"Telegram Group: {TELEGRAM_GROUP_URL}\n"
        f"Telegram Channel: {TELEGRAM_CHANNEL_URL}\n"
        f"Discord: {DISCORD_URL}"
    )


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📌 {PROJECT_NAME} Community Rules\n\n"
        f"1. No scam or phishing links.\n"
        f"2. Never share private keys or seed phrases.\n"
        f"3. No spam, abusive language, or impersonation.\n"
        f"4. {POINT_NAME} is a community point before SPNX token launch.\n"
        f"5. Final SPNX conversion policy will be officially announced later.\n\n"
        f"경고 {MAX_WARNINGS}회 이상이면 차단될 수 있습니다."
    )


async def mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌐 Visit Website +100", url=WEBSITE_URL)],
        [InlineKeyboardButton("📢 Join Telegram Channel +200", url=TELEGRAM_CHANNEL_URL)],
        [InlineKeyboardButton("💬 Join Telegram Group +200", url=TELEGRAM_GROUP_URL)],
        [InlineKeyboardButton("▶ Subscribe YouTube +300", url=YOUTUBE_URL)],
        [InlineKeyboardButton("𝕏 Follow X +300", url=X_URL)],
        [InlineKeyboardButton("🎮 Join Discord +300", url=DISCORD_URL)],
    ]

    await update.message.reply_text(
        f"🎯 {PROJECT_NAME} Missions\n\n"
        f"After completing each mission, type:\n\n"
        f"/done website\n"
        f"/done telegram_channel\n"
        f"/done telegram_group\n"
        f"/done youtube\n"
        f"/done x\n"
        f"/done discord\n\n"
        f"⚠️ Early version: missions are recorded by user confirmation. Admin review is recommended before final SPNX conversion.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)

    if not context.args:
        await update.message.reply_text("Usage: /done mission_name\nExample: /done youtube")
        return

    mission_key = context.args[0].strip().lower()

    if mission_key not in MISSION_REWARDS:
        await update.message.reply_text("Invalid mission. Use /mission to see available missions.")
        return

    success = complete_mission_once(user.id, mission_key)

    if not success:
        await update.message.reply_text("This mission was already completed.")
        return

    await update.message.reply_text(
        f"✅ Mission completed: {mission_key}\n"
        f"Reward: +{MISSION_REWARDS[mission_key]} {POINT_NAME}"
    )


async def mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)
    row = get_user(user.id)

    if row["last_mining_at"]:
        last = datetime.fromisoformat(row["last_mining_at"])
        next_time = last + timedelta(hours=MINING_HOURS)

        if now() < next_time:
            remaining = next_time - now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await update.message.reply_text(
                f"⛏️ Mining is already active.\n\n"
                f"Next mining available in: {hours}h {minutes}m"
            )
            return

    conn = db()
    conn.execute("UPDATE users SET points = points + ?, last_mining_at=? WHERE user_id=?", (MINING_REWARD, now_iso(), user.id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"⛏️ Mining completed!\n\n"
        f"Reward: +{MINING_REWARD} {POINT_NAME}\n"
        f"Come back after {MINING_HOURS} hours."
    )


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)
    row = get_user(user.id)

    await update.message.reply_text(
        f"💎 Your {PROJECT_NAME} Balance\n\n"
        f"Points: {row['points']} {POINT_NAME}\n"
        f"Referrals: {referral_count(user.id)}\n"
        f"Solana Wallet: {row['wallet'] if row['wallet'] else 'Not registered'}"
    )


async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)

    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    await update.message.reply_text(
        f"👥 Your referral link:\n{link}\n\n"
        f"Referral reward: +500 {POINT_NAME}\n"
        f"Your referrals: {referral_count(user.id)}"
    )


async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    rows = conn.execute("""
        SELECT user_id, username, first_name, points
        FROM users
        ORDER BY points DESC
        LIMIT 10
    """).fetchall()
    conn.close()

    text = f"🏆 {PROJECT_NAME} Ranking TOP 10\n\n"
    for i, row in enumerate(rows, 1):
        name = f"@{row['username']}" if row["username"] else row["first_name"] or str(row["user_id"])
        text += f"{i}. {name} - {row['points']} {POINT_NAME}\n"

    await update.message.reply_text(text)


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user)

    if not context.args:
        await update.message.reply_text("Usage: /wallet your_solana_wallet_address")
        return

    wallet_address = context.args[0].strip()

    if not SOLANA_RE.match(wallet_address):
        await update.message.reply_text("Invalid Solana wallet address.")
        return

    row = get_user(user.id)
    first_time = not row["wallet"]

    conn = db()
    conn.execute("UPDATE users SET wallet=? WHERE user_id=?", (wallet_address, user.id))
    conn.commit()
    conn.close()

    if first_time:
        add_points(user.id, 200)

    await update.message.reply_text(
        f"✅ Solana wallet registered.\n\n"
        f"{wallet_address}\n\n"
        f"Reward: {'+200 ' + POINT_NAME if first_time else 'Already registered'}"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    wallets = conn.execute("SELECT COUNT(*) AS c FROM users WHERE wallet IS NOT NULL AND wallet != ''").fetchone()["c"]
    total_points = conn.execute("SELECT COALESCE(SUM(points), 0) AS s FROM users").fetchone()["s"]
    conn.close()

    await update.message.reply_text(
        f"📊 {PROJECT_NAME} Stats\n\n"
        f"Users: {users}\n"
        f"Wallets: {wallets}\n"
        f"Total Points: {total_points} {POINT_NAME}"
    )


async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only.")
        return

    conn = db()
    rows = conn.execute("""
        SELECT user_id, username, first_name, points, wallet, referrer_id, joined_at
        FROM users
        ORDER BY points DESC
    """).fetchall()
    conn.close()

    path = Path("spacenovax_points_export.csv")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "username", "first_name", "points", "solana_wallet", "referrer_id", "referral_count", "joined_at"])
        for r in rows:
            writer.writerow([r["user_id"], r["username"], r["first_name"], r["points"], r["wallet"], r["referrer_id"], referral_count(r["user_id"]), r["joined_at"]])

    await update.message.reply_document(document=path.open("rb"), filename="spacenovax_points_export.csv")


async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    upsert_user(msg.from_user)

    if is_admin(msg.from_user.id):
        return

    text = msg.text.lower()

    if LINK_RE.search(text):
        try:
            await msg.delete()
        except Exception:
            pass

        count = add_warning(msg.chat_id, msg.from_user.id)
        await context.bot.send_message(
            chat_id=msg.chat_id,
            text=f"⚠️ Unsafe message removed. Warning {count}/{MAX_WARNINGS}"
        )

        if count >= MAX_WARNINGS:
            await context.bot.ban_chat_member(msg.chat_id, msg.from_user.id)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in .env file.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    for cmd, func in [
        ("start", start),
        ("about", about),
        ("rules", rules),
        ("mission", mission),
        ("done", done),
        ("mine", mine),
        ("points", points),
        ("ref", ref),
        ("rank", rank),
        ("wallet", wallet),
        ("stats", stats),
        ("export", export),
    ]:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate))

    print(f"{PROJECT_NAME} Mining Points Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
