import json
import re
import httpx
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8056128763:AAEeDHiCsXseo58jP6sVBsSv4WEYM3FZeQo"
ADMIN_ID = 6177293322
CREDITS_FILE = "credits.json"

blocked_numbers = {
    "9870965087",
    "+919870965087",
    "919870965087"
}

def normalize_number(num):
    num = num.strip().replace("+91", "")
    if num.startswith("91") and len(num) == 12:
        num = num[2:]
    return num

def extract_mobile(text):
    pattern = r'(?:\+91|91)?\s*([6-9]\d{9})'
    match = re.search(pattern, text.replace(" ", "").replace("-", ""))
    if match:
        return match.group(1)
    return None

def load_credits():
    try:
        with open(CREDITS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_credits(credits):
    with open(CREDITS_FILE, "w") as f:
        json.dump(credits, f)

credits = load_credits()

START_MSG = (
    "<b>\n"
    " • NUMBER TO INFORMATION •\n"
    "\n</b>"
    "  <code>/info - Check Number\n</code>"
    "  <code>/credits - Check Credits\n</code>"
    "\n"
    "<a href=\"https://t.me/S4J4G\">\u200b</a>"
)

def reply_to_cmd(update, text, **kwargs):
    return update.message.reply_text(
        text,
        reply_to_message_id=update.message.message_id,
        **kwargs
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        START_MSG,
        disable_web_page_preview=False,
        reply_to_message_id=update.message.message_id
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return await reply_to_cmd(update, "❌ Only admin can use this command.")
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        return await reply_to_cmd(update, "Usage: /add <user_id> <credits>")
    target_id = str(context.args[0])
    count = int(context.args[1])
    credits[target_id] = credits.get(target_id, 0) + count
    save_credits(credits)
    await reply_to_cmd(update, f"✅ Added {count} credits to user {target_id} (Total: {credits[target_id]}).")

    try:
        receipt_id = f"#CR{datetime.now().strftime('%y%m%d%H%M%S')}"
        time_str = datetime.now().strftime("%d %b %Y, %H:%M")
        credit_msg = (
            "<b>━━━━━━━━━━━━━━━━━━━━━</b>\n"
            "              <b>CREDIT RECEIPT</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<b>Receipt ID:</b> <code>{receipt_id}</code>\n"
            f"<b>Time:</b> <code>{time_str}</code>\n"
            f"<b>Account:</b> <code>{target_id}</code>\n"
            f"<b>Credits Added:</b> <b>{count}</b>\n"
            f"<b>Current Balance:</b> <b>{credits[target_id]}</b>\n\n"
            "<b>Status:</b> <code>PAID</code>\n\n"
            "<i>Thank you for your purchase!\nEnjoy using /info for your searches.</i>\n"
            
        )
        await context.bot.send_message(
            chat_id=int(target_id),
            text=credit_msg,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
    except Exception:
        pass

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return await reply_to_cmd(update, "❌ Only admin can use this command.")
    if len(context.args) != 1 or not context.args[0].isdigit():
        return await reply_to_cmd(update, "Usage: /remove <user_id>")
    target_id = str(context.args[0])
    credits[target_id] = 0
    save_credits(credits)
    await reply_to_cmd(update, f"✅ Removed all credits from user {target_id}.")

async def check_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    count = credits.get(uid, 0)
    await update.message.reply_text(
        f"💳 You have <b>{count}</b> credits.",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asyncio.create_task(run_info(update, context))

async def run_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    is_admin = uid == str(ADMIN_ID)

    if not is_admin and credits.get(uid, 0) < 1:
        return await reply_to_cmd(update, "❌ You have 0 credits. Contact admin.")

    if not context.args:
        return await reply_to_cmd(update, "Usage: /info <number or text>")
    text = " ".join(context.args)
    number = extract_mobile(text)
    if not number:
        return await reply_to_cmd(update, "❌ Number not found in database.")

    check_number = normalize_number(number)
    all_variants = {check_number, f"+91{check_number}", f"91{check_number}"}
    if blocked_numbers & all_variants:
        return await reply_to_cmd(update, "❌ Number not found in database.")

    user_disp = (
        f"@{update.effective_user.username}"
        if update.effective_user.username else update.effective_user.first_name or "User"
    )

    loading_msg = await update.message.reply_html(
        f"<b>Please wait...</b>",
        reply_to_message_id=update.message.message_id
    )

    url = f"https://glonova.in/os.php/?ng={number}"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(url)
            data = resp.json()
    except Exception:
        return await loading_msg.edit_text("❌ Number not found in database.")

    if not data.get("success") or not data.get("data", {}).get("results"):
        return await loading_msg.edit_text("❌ Number not found in database.")

    if not is_admin:
        credits[uid] = credits.get(uid, 0) - 1
        if credits[uid] < 0:
            credits[uid] = 0
        save_credits(credits)

    result = data["data"]["results"][0]
    msg = [
        f"<b>📱 Mobile:</b> <code>{result.get('📱 Mobile', '-')}</code>",
        f"<b>👤 Name:</b> <code>{result.get('👤 Name', '-')}</code>",
        f"<b>👨‍👦 Father Name:</b> <code>{result.get('👨‍👦 Father Name', '-')}</code>",
        f"<b>🏠 Address:</b> <code>{result.get('🏠 Address', '-').replace('!!',' ').replace('!',' ')}</code>",
        f"<b>📞 Alt Number:</b> <code>{result.get('📞 Alt Number', '-')}</code>",
        f"<b>📍 Circle:</b> <code>{result.get('📍 Circle', '-')}</code>",
        f"<b>🆔 Aadhar Card:</b> <code>{result.get('🆔 Aadhar Card', '-')}</code>",
        f"<b>📧 Email:</b> <code>{result.get('📧 Email', '-')}</code>",
    ]
    await loading_msg.edit_text('\n'.join(msg), parse_mode="HTML")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("credits", check_credits))
    app.add_handler(CommandHandler("info", info))
    print("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
