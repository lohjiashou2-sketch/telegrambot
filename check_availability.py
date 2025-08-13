import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()

def check_facility_availability(facility_name, date):
    session = requests.Session()

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

    login_url = "https://web.tarc.edu.my/portal/loginProcess.jsp"
    payload = {
        "username": os.getenv("LOGIN_USERNAME"),
        "password": os.getenv("LOGIN_PASSWORD"),
    }

    login_response = session.post(login_url, data=payload)
    if "Dashboard" not in login_response.text:
        return "❌ Login failed!"

    event_id = "8D7392FB-6BCF-449A-AA79-3F19B607E892"
    venue_type_id = venue_id[facility_name]

    url = f"https://web.tarc.edu.my/portal/facilityBooking/AJAXCalendar.jsp?act=list&event_id={event_id}&fdate={date}&venue_type_id={venue_type_id}"
    response = session.get(url)

    try:
        json_data = response.json()
    except Exception:
        return "❌ Failed to fetch booking data. Try again later."

    html = f"<table>{json_data['header']}{json_data['content']}</table>"
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    if len(rows) < 4:
        return "ℹ️ No data available."

    top_row = rows[0].find_all("td")[1:]
    bottom_row = rows[1].find_all("td")

    time_ranges = []
    for idx, (t1, t2) in enumerate(zip(top_row, bottom_row)):
        start = t1.get_text(strip=True)
        end = t2.get_text(strip=True)
        if idx < 3:
            start += "AM"
            end += "AM"
        elif idx == 3:
            start += "AM"
            end += "PM"
        else:
            start += "PM"
            end += "PM"
        time_ranges.append(f"{start} - {end}")

    available_found = False
    available_slots = []
    result = f"\n📅  Date: {date}\n🏟️  Facility: {facility_name.capitalize()}\n"
    result += "\n🟢 Available Slots:\n"

    for row in rows[3:]:
        cols = row.find_all("td")
        venue = cols[0].get_text(strip=True)
        time_index = 0
        for col in cols[1:]:
            colspan = int(col.get("colspan", 1))
            style = col.get("style", "")
            if "#009624" in style:
                for _ in range(colspan):
                    available_found = True
                    time_label = time_ranges[time_index]
                    available_slots.append(time_label)
                    result += f"✅ {venue} | {time_label}\n"
                    time_index += 1
            else:
                time_index += colspan

    if not available_found:
        result = "❌ No available slots."

    return (result, list(set(available_slots)))


#print(check_facility_availability("badminton", "11/08/2025"))