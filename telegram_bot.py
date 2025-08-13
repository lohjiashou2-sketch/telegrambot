from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from check_availability import check_facility_availability 
import bot_booking
import database
from datetime import datetime, timedelta
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

FACILITY, DATE, TIME, USERNAME, PASSWORD, CONFIRM = range(6)

FACILITIES = ["badminton", "pickleball", "tennis", "pingpong", "snooker", "futsal", "squash", "karaoke_room"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 Hello! I’m the TARUMT Facility Booking Bot.\n\n"
        "Type the number of the facility you want to book:\n"
        "1. badminton\n"
        "2. pickleball\n"
        "3. tennis\n"
        "4. ping pong\n"
        "5. snooker\n"
        "6. futsal\n"
        "7. squash\n"
        "8. karaoke room"
    )
    await update.message.reply_text(welcome)
    return FACILITY

async def receive_facility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    if not user_input.isdigit() or not 1 <= int(user_input) <= len(FACILITIES):
        await update.message.reply_text("❌ Please enter a number from 1 to 8 to choose a facility.")
        return FACILITY

    facility_index = int(user_input) - 1
    facility = FACILITIES[facility_index]

    context.user_data["facility"] = facility

    await update.message.reply_text(f"✅ You selected: {facility.capitalize()}.\nPlease enter the date in DD/MM/YYYY format (e.g. 29/07/2025):")
    return DATE

async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    facility = context.user_data.get("facility")

    try:
        # Parse and validate date format
        parsed_date = datetime.strptime(user_input, "%d/%m/%Y")
        today = datetime.now().date()
        max_booking_date = today + timedelta(days=4)

        if parsed_date.date() < today:
            await update.message.reply_text("❌ The date is in the past. Please enter today’s date or a future date.")
            return DATE

        if parsed_date.date() > max_booking_date:
            await update.message.reply_text("❌ You can only book up to 5 days in advance. Please enter a closer date.")
            return DATE

    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please enter the date in DD/MM/YYYY format (e.g. 29/07/2025).")
        return DATE

    context.user_data["date"] = user_input

    result_message, available_times = check_facility_availability(facility, user_input)
    if not available_times:
        await update.message.reply_text(result_message)
        return ConversationHandler.END

    context.user_data["date"] = user_input
    context.user_data["available_slots"] = available_times

    # Send availability
    await update.message.reply_text(result_message)

    # Prompt for time
    await update.message.reply_text(
        "🕐 Please select a time slot:",
        reply_markup=ReplyKeyboardMarkup([[t] for t in available_times], resize_keyboard=True)
    )

    return TIME

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    available_slots = context.user_data.get("available_slots", [])

    valid_slots = [slot.strip() for slot in available_slots]

    if user_input not in valid_slots:
        await update.message.reply_text(
            "❌ Invalid time slot. Please choose a valid one from the list provided.",
            reply_markup=ReplyKeyboardMarkup(
                [[slot] for slot in valid_slots], resize_keyboard=True
            )
        )
        return TIME
    
    context.user_data["time"] = user_input
    await update.message.reply_text("Please type your student intranet username:", reply_markup=ReplyKeyboardRemove())
    return USERNAME

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["username"] = update.message.text.strip()
    await update.message.reply_text("Please type your student intranet password:")
    return PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["password"] = update.message.text.strip()

    username = context.user_data.get("username")
    password = context.user_data.get("password")

    # Try to login right away
    try:
        session = requests.Session()
        session = bot_booking.login_as(session, username, password)
        context.user_data["session"] = session
    except Exception:
        await update.message.reply_text(
            "❌ Login failed. Your username or password may be incorrect.\n\n"
            "Please type your student intranet username again:"
        )
        return USERNAME  # Go back to username step for retry

    # If login is successful, move to confirmation
    facility = context.user_data.get("facility")
    date = context.user_data.get("date")
    time = context.user_data.get("time")

    await update.message.reply_text(
        f"✅ You have selected:\n"
        f"Facility: {facility}\n"
        f"Date: {date}\n"
        f"Time: {time}\n\n"
        "Please type 'yes' to confirm or 'no' to cancel.",
        reply_markup=ReplyKeyboardRemove()
    )

    return CONFIRM

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().lower()

    if user_input not in ["yes", "no"]:
        await update.message.reply_text("❌ Please reply with 'yes' or 'no'.")
        return CONFIRM

    if user_input == "no":
        await update.message.reply_text("❌ Booking canceled.")
        return ConversationHandler.END

    # Retrieve session from earlier login
    session = context.user_data.get("session")
    facility = context.user_data.get("facility")
    date = context.user_data.get("date")
    time = context.user_data.get("time")
    username = context.user_data.get("username")
    password = context.user_data.get("password")

    # Immediate booking or scheduled booking logic
    if datetime.strptime(date, "%d/%m/%Y").date() > datetime.now().date() + timedelta(days=2):
        database.save_future_booking(username, password, facility, date, time, "pending")
        await update.message.reply_text(
            f"✅ Your booking has been scheduled:\nFacility: {facility}\nDate: {date}\nTime: {time}"
        )
    else:
        result_message = bot_booking.book_venue(session, facility, date, time)
        database.save_future_booking(username, password, facility, date, time, "booked")
        await update.message.reply_text(result_message)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Booking process canceled.")
    return ConversationHandler.END

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        FACILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_facility)],
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_booking)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)
app.run_polling()