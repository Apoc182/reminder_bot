import requests
from dataclasses import dataclass
from urllib.parse import urljoin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from time import sleep
from model import ScheduledReminder
from datetime import datetime, timedelta
import os
from tabulate import tabulate


TOKEN = os.environ["TOKEN"]
URL = os.environ["URL"] + TOKEN + "/"
DATABASE_STRING = os.environ["DATABASE_STRING"]
SNOOZE_MINUTES = int(os.environ["SNOOZE_MINUTES"])
CHAT_ID = os.environ["CHAT_ID"]
RESET_TIME = os.environ["RESET_TIME"]
NEW_REMINDER_MESSAGE_DELIMITER = os.environ.get("NEW_REMINDER_MESSAGE_DELIMITER", "|")
POLL_TIME = int(os.environ.get("POLL_TIME", 60))

print(URL)

@dataclass
class Response:
    message: str
    reply_id: int|None = None   

def get_now_timestring() -> str:
    return encode_timestring(datetime.now())

def decode_timestring(time_string: str) -> datetime:
    return datetime.strptime(time_string, "%H%M")

def encode_timestring(time: datetime) -> str:
    return time.strftime("%H%M")

def get_responses() -> list[Response]:
    r = requests.get(urljoin(URL, "getUpdates"))
    output = []
    highest_update_id = 0
    for response in r.json()["result"]:
        message = response["message"]
        command = message["text"]
        if "reply_to_message" in message:
            reply_id = message["reply_to_message"]["message_id"]
        else:
            reply_id = None
        output.append(Response(message=command, reply_id=reply_id))
        highest_update_id = response["update_id"]
    requests.get(urljoin(URL, "getUpdates"), params={"offset" : highest_update_id + 1})
    return output

def process_responses(session: Session, responses: list[Response], now: str) -> None: 
    print(responses)
    for response in responses:
        if response.reply_id:
            reminder = session.query(ScheduledReminder).filter(ScheduledReminder.notification_id==response.reply_id).first()
            if not reminder:
                continue
            if response.message.lower() == "y":
                reminder.completed = True
                reminder.snooze_until = ""
            elif response.message.isdigit():
                reminder.snooze_until = response.message
        else:
            if response.message.lower() == "list":
                result = session.query(
                    ScheduledReminder.name, 
                    ScheduledReminder.time, 
                    ScheduledReminder.snooze_until).filter(
                    ScheduledReminder.completed == False).order_by(
                    ScheduledReminder.time).all()
                

                
                def int_or_zero(i: str) -> int:
                    try:
                        return int(i)
                    except ValueError:
                        return 0

                table = [dict(zip(('name', 'time', 'snooze_until'), row)) for row in result if int_or_zero(row[1]) > int(now) or int_or_zero(row[2]) > int(now)]
                print(table)
                if not table:
                    send_message("No reminders left today!")
                    continue
                table_str = tabulate(table, headers='keys', tablefmt="pipe")
                escaped_table_str = table_str.translate(str.maketrans({i: '\\' + i for i in r'_*[]()~`>#+-=|{}.!'}))
                send_message(f"```\n{escaped_table_str}\n```", markdown=True)
            else:
                name, time, daily = response.message.split(NEW_REMINDER_MESSAGE_DELIMITER)
                daily = True if daily == "1" else False
                sr = ScheduledReminder(name=name, daily=daily, time=time, completed=False, snooze_until="")
                session.add(sr)



    session.commit()
# encode_timestring(decode_timestring(get_now_timestring()) + timedelta(minutes=SNOOZE_MINUTES))

def process_reminders(session: Session, now: str):
    
    # Need to get everything which is not completed.
    reminders: list[ScheduledReminder] = session.query(ScheduledReminder).filter(ScheduledReminder.completed == False)


    # Then, if snoozed is populated, use that time, otherwise use the other time.
    for reminder in reminders:
        alert_time = reminder.snooze_until if reminder.snooze_until else reminder.time

        # If it is that given time, send the notification and update snoozed to now + snooze time.
        if alert_time == now:
            reminder.notification_id = send_message(f"Reminder: {reminder.name}")
            reminder.snooze_until = encode_timestring(decode_timestring(now) + timedelta(minutes=SNOOZE_MINUTES))

    session.commit()
    

def send_message(text: str, markdown=False) -> int:
    p = {"text": text, "chat_id": CHAT_ID}
    if markdown:
        p.update({"parse_mode": "MarkdownV2"})
    return requests.get(
        urljoin(URL, "sendMessage"),
        params=p
    ).json()["result"]["message_id"]

def process_reset(session: Session, now: str):
    if now == RESET_TIME:
        session.query(ScheduledReminder).filter(ScheduledReminder.daily == True).update({ScheduledReminder.completed : False})

def main(session_maker):
    session = session_maker()
    send_message(f"Application started. Serving {len(session.query(ScheduledReminder).all())} reminders.\nLocal time: {datetime.now()}")
    session.close()

    while True:
        print("loop")
        now = get_now_timestring()
        responses = get_responses()
        session = session_maker()
        process_responses(session, responses, now)
        process_reminders(session, now)
        process_reset(session, now)
        print("waiting.")
        session.close()
        sleep(POLL_TIME)

if __name__ == "__main__":
    engine = create_engine(DATABASE_STRING)
    SessionFactory = sessionmaker(bind=engine)
    main(SessionFactory)