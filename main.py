
import os
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==========================================
# 1. CONFIGURATION
# ==========================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ADMIN_USER_ID = int(
    os.getenv("ADMIN_USER_ID", "0")
)

BASE_DIR = Path(__file__).resolve().parent

FAQ_FILE = (
    BASE_DIR / "knowledge_base" / "faq.json"
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==========================================
# 2. LOAD FAQ DATABASE
# ==========================================

def load_faq():

    if not FAQ_FILE.exists():
        raise FileNotFoundError(
            f"FAQ file not found: {FAQ_FILE}"
        )

    with open(
        FAQ_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    faqs = data.get("faqs", [])

    if not faqs:
        raise ValueError("No FAQ entries found.")

    for item in faqs:

        if not all(
            key in item
            for key in ("category", "questions", "answer")
        ):
            raise ValueError(
                "Every FAQ must have category, questions and answer."
            )

        if not item["questions"]:
            raise ValueError(
                "Every FAQ must contain at least one question."
            )

    print(f"Loaded {len(faqs)} FAQ entries.")

    return faqs


FAQ_DATABASE = load_faq()

# ==========================================
# 3. CATEGORY ICONS
# ==========================================

CATEGORY_ICONS = {
    "Working Hours": "🕒",
    "Job Interview": "🤝",
    "Location": "📍",
    "Job Application": "📄",
    "Job Vacancies": "💼",
    "Internship": "🎓",
    "Job Requirements": "📋",
    "Salary & Benefits": "💰",
    "Contact HR": "☎️"
}

def get_categories():

    return list(dict.fromkeys(
        item["category"]
        for item in FAQ_DATABASE
    ))


# ==========================================
# 4. CATEGORY KEYBOARD
# ==========================================

def category_keyboard():

    categories = get_categories()

    buttons = []

    for index, category in enumerate(categories):

        icon = CATEGORY_ICONS.get(
            category,
            "📌"
        )

        buttons.append(
            InlineKeyboardButton(
                f"{icon} {category}",
                callback_data=f"cat:{index}"
            )
        )

    keyboard = []

    # Display two categories per row
    for i in range(0, len(buttons), 2):

        keyboard.append(
            buttons[i:i + 2]
        )

    return InlineKeyboardMarkup(keyboard)


# ==========================================
# 5. QUESTION KEYBOARD
# ==========================================

def question_keyboard(category_index):

    categories = get_categories()

    if category_index >= len(categories):
        return category_keyboard()

    selected_category = categories[category_index]

    buttons = []

    for index, item in enumerate(FAQ_DATABASE):

        if item["category"] == selected_category:

            question = item["questions"][0]

            buttons.append([
                InlineKeyboardButton(
                    f"❓ {question[:60]}",
                    callback_data=f"q:{index}"
                )
            ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Back to Categories",
            callback_data="home"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ==========================================
# 6. START COMMAND
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    welcome_message = (
        "👋 Welcome to RMA Cambodia Career Assistant!\n\n"
        "We are happy to help you learn more about "
        "career opportunities at RMA Cambodia.\n\n"
        "Please select a category below to explore "
        "frequently asked questions.\n\n"
        "សូមជ្រើសរើសប្រភេទព័ត៌មានខាងក្រោម "
        "ដើម្បីស្វែងរកចម្លើយ។"
    )

    await update.message.reply_text(
        welcome_message,
        reply_markup=category_keyboard()
    )


# ==========================================
# 7. HANDLE CATEGORY AND QUESTION CLICKS
# ==========================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # Return to main category menu
    if data == "home":

        await query.edit_message_text(
            "📚 RMA Cambodia Career Assistant\n\n"
            "Please select a category:",
            reply_markup=category_keyboard()
        )

        return

    # Open selected category
    if data.startswith("cat:"):

        category_index = int(data.split(":")[1])

        categories = get_categories()

        if category_index >= len(categories):
            await query.answer(
                "Category not found.",
                show_alert=True
            )
            return

        category = categories[category_index]

        icon = CATEGORY_ICONS.get(
            category,
            "📌"
        )

        await query.edit_message_text(
            f"{icon} {category}\n\n"
            "Please select your question:",
            reply_markup=question_keyboard(
                category_index
            )
        )

        return

    # Display selected question's answer
    if data.startswith("q:"):

        faq_index = int(data.split(":")[1])

        if faq_index >= len(FAQ_DATABASE):
            await query.answer(
                "Question not found.",
                show_alert=True
            )
            return

        item = FAQ_DATABASE[faq_index]

        category = item["category"]

        category_index = get_categories().index(category)

        icon = CATEGORY_ICONS.get(
            category,
            "📌"
        )

        answer_message = (
            f"{icon} {category}\n\n"
            f"{item['answer']}\n\n"
            "━━━━━━━━━━━━━━\n"
            "Did this answer help you?\n"
            "តើចម្លើយនេះមានប្រយោជន៍ដែរឬទេ?"
        )

        keyboard = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "⬅️ Back to Questions",
                    callback_data=f"cat:{category_index}"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
                    callback_data="home"
                )
            ]

        ])

        await query.edit_message_text(
            answer_message,
            reply_markup=keyboard
        )


# ==========================================
# 8. HELP COMMAND
# ==========================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Please select a category using /start.\n\n"
        "You can browse job applications, "
        "working hours, interviews and more."
    )


# ==========================================
# 9. ADMIN RELOAD COMMAND
# ==========================================

async def reload_faq(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if (
        ADMIN_USER_ID == 0
        or update.effective_user.id != ADMIN_USER_ID
    ):

        await update.message.reply_text(
            "⛔ You are not authorized to reload FAQs."
        )

        return

    global FAQ_DATABASE

    try:

        new_database = load_faq()

        FAQ_DATABASE = new_database

        await update.message.reply_text(
            "✅ FAQ database updated successfully!\n\n"
            f"Total FAQ entries: {len(FAQ_DATABASE)}\n"
            f"Total categories: {len(get_categories())}"
        )

    except Exception:

        logging.exception("FAQ reload error")

        await update.message.reply_text(
            "❌ Failed to reload FAQ database. "
            "Please check faq.json."
        )


# ==========================================
# 10. HANDLE TEXT MESSAGES
# ==========================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Please select a category below to find "
        "the information you need.\n\n"
        "សូមជ្រើសរើសប្រភេទព័ត៌មានខាងក្រោម។",
        reply_markup=category_keyboard()
    )


# ==========================================
# 11. ERROR HANDLER
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logging.error(
        "Telegram application error",
        exc_info=context.error
    )


# ==========================================
# 12. RUN BOT
# ==========================================

def main():

    if not TELEGRAM_TOKEN:
        raise ValueError(
            "Telegram token is missing in .env"
        )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("reload", reload_faq)
    )

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    application.add_error_handler(error_handler)

    print("RMA Cambodia Career Bot is running!")
    print(f"FAQ entries: {len(FAQ_DATABASE)}")
    print(f"Categories: {len(get_categories())}")

    application.run_polling()


if __name__ == "__main__":
    main()
