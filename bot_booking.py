from datetime import datetime

login_url = "https://web.tarc.edu.my/portal/loginProcess.jsp"
booking_url = "https://web.tarc.edu.my/portal/facilityBooking/AJAXBooking.jsp"

venue_id = {
    "badminton": "123BB4B8-342A-4324-BD94-74426B8ADA7F",
    "pickleball": "03272312-A8BF-4794-8596-34C1AB96CAF0",
    "tennis": "D241483A-B28F-46DB-9451-36C100B38604",
    "pingpong": "12A4DBEA-83BF-404B-9840-D83E08748174",
    "snooker": "068CB72D-1A42-4488-87A0-B65591D687EE",
    "futsal": "ECBDF6C0-DA0C-4301-8BC6-537A25C97260",
    "squash": "7173F10B-ACC2-49FE-BA0F-29E2E235F0CE",
    "karaoke_room": "FFBA42DE-ABC0-4DE6-AAD1-E887554230C5"
}

def login_as(session, username, password):
    
    credentials = {"username": username, "password": password}
    response = session.post(login_url, data=credentials)

    if "Dashboard" in response.text:
        print("Login successful.")
    else:
        print("Login failed.")
        raise Exception("Login failed")

    return session

def book_venue(session, facility, date, time):

    venue_type_id = venue_id[facility]

    start_str, end_str = [t.strip() for t in time.split(" - ")]

    start_time = datetime.strptime(start_str, "%I:%M%p").strftime("%H:%M")
    end_time = datetime.strptime(end_str, "%I:%M%p").strftime("%H:%M")

    booking_payload = {
        "act": "insert",
        "event_id": "8D7392FB-6BCF-449A-AA79-3F19B607E892",
        "fpaxno": "1",
        "venuex_type_id": venue_type_id,
        "fstarttime": start_time,
        "fendtime": end_time,
        "fbkdate": date,
    }

    response = session.post(booking_url, data=booking_payload)

    try:
        if "success" in response.text.lower():
            result = "✅ Booking Successful"
        else:
            result = "❌ Booking Failed"
    except Exception as e:
        result = f"Error checking booking status: {e}"

    return result