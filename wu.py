import smtplib
import random
import time
import schedule
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# =========================
# LOGGING CONFIGURATION
# =========================
logging.basicConfig(
    filename="warmup.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def log(message, level="info"):
    print(message)
    if level == "info":
        logging.info(message)
    elif level == "error":
        logging.error(message)


# =========================
# SMTP CONFIG
# =========================
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))

MAIL1 = os.getenv("MAIL1")
PASS1 = os.getenv("PASS1")

MAIL2 = os.getenv("MAIL2")
PASS2 = os.getenv("PASS2")

SUBJECTS = [
    "Quick check",
    "Following up",
    "Small question",
    "Just confirming",
    "Need your input"
]

BODIES = [
    "Hey, just checking this.",
    "Please confirm once.",
    "Sharing this for review.",
    "Let me know your thoughts.",
    "Waiting for your response."
]

DAILY_LIMIT = 10
sent_today = 0


def send_email(sender, password, receiver):
    subject = random.choice(SUBJECTS)
    body = random.choice(BODIES)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        log(f"SUCCESS | {sender} → {receiver} | Subject: {subject}")

    except Exception as e:
        log(f"ERROR | {sender} → {receiver} | {str(e)}", level="error")


def warmup_job():
    global sent_today

    if sent_today >= DAILY_LIMIT:
        log("Daily limit reached.")
        return

    if random.choice([True, False]):
        send_email(MAIL1, PASS1, MAIL2)
    else:
        send_email(MAIL2, PASS2, MAIL1)

    sent_today += 1
    log(f"Daily Sent Count: {sent_today}/{DAILY_LIMIT}")

    delay = random.randint(300, 1200)  # 5–20 min delay
    log(f"Sleeping for {delay} seconds...")
    time.sleep(delay)


schedule.every(1).minutes.do(warmup_job)

log("🔥 Dual Gmail Warm-Up Started...")

while True:
    schedule.run_pending()
    time.sleep(5)
