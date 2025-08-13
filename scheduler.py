from database import get_db_connection, decrypt_password
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import requests
import bot_booking

def get_future_bookings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, encrypted_password, facility, booking_date, booking_time FROM bookings WHERE status = 'pending'")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    bookings = []
    for row in rows:
        booking_id, username, enc_pw, facility, date, time = row
        password = decrypt_password(enc_pw)
        bookings.append({
            "id": booking_id,
            "username": username,
            "password": password,
            "facility": facility,
            "date": date,
            "time": time
        })
    return bookings

def mark_booking_status(booking_id, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET status = %s WHERE id = %s", (status, booking_id))
    conn.commit()
    cur.close()
    conn.close()

def wait_until_midnight():
    while True:
        now = datetime.now()
        if now.strftime("%H:%M:%S") == "00:00:00":
            break

def execute_scheduled_bookings():
    today = datetime.now().date()
    allowed_window = today + timedelta(days=3)

    for booking in get_future_bookings():
        if booking["date"] <= allowed_window:
            try:
                wait_until_midnight()
                session = requests.Session()
                session = bot_booking.login_as(session, booking["username"], booking["password"])
                result = bot_booking.book_venue(session, booking["facility"], booking["date"], booking["time"])
                mark_booking_status(booking["id"], "booked" if result else "failed")
            except Exception as e:
                mark_booking_status(booking["id"], "failed")

scheduler = BackgroundScheduler()
scheduler.add_job(execute_scheduled_bookings, 'interval', minutes=1)
scheduler.start()