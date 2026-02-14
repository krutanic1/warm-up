import os
import random
import smtplib
import logging
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional local dev dependency
    load_dotenv = None

if load_dotenv:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

MAIL1 = os.getenv("MAIL1")
PASS1 = os.getenv("PASS1")

MAIL2 = os.getenv("MAIL2")
PASS2 = os.getenv("PASS2")

KV_REST_API_URL = os.getenv("KV_REST_API_URL")
KV_REST_API_TOKEN = os.getenv("KV_REST_API_TOKEN")
import tempfile

LOCAL_STATE_PATH = os.getenv(
    "LOCAL_STATE_PATH",
    os.path.join(tempfile.gettempdir(), ".warmup_state.json"),
)

DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "10"))
MIN_INTERVAL_SECONDS = int(os.getenv("MIN_INTERVAL_SECONDS", "1800"))

SUBJECTS = [
    "Quick check",
    "Following up",
    "Small question",
    "Just confirming",
    "Need your input",
]

BODIES = [
    "Hey, just checking this.",
    "Please confirm once.",
    "Sharing this for review.",
    "Let me know your thoughts.",
    "Waiting for your response.",
]


def kv_headers():
    return {
        "Authorization": f"Bearer {KV_REST_API_TOKEN}",
        "Content-Type": "application/json",
    }


def use_kv():
    return bool(KV_REST_API_URL and KV_REST_API_TOKEN)


def load_local_state():
    if not os.path.exists(LOCAL_STATE_PATH):
        return {}
    try:
        with open(LOCAL_STATE_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        logging.warning("Failed to load local state: %s", exc)
        return {}


def save_local_state(state):
    try:
        with open(LOCAL_STATE_PATH, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    except Exception as exc:
        logging.warning("Failed to save local state: %s", exc)


def kv_get(key):
    if not use_kv():
        state = load_local_state()
        return state.get(key)

    url = f"{KV_REST_API_URL}/get/{key}"
    response = requests.get(url, headers=kv_headers(), timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("result")


def kv_set(key, value, ex_seconds=None):
    if not use_kv():
        state = load_local_state()
        state[key] = value
        save_local_state(state)
        return

    url = f"{KV_REST_API_URL}/set/{key}/{value}"
    params = {}
    if ex_seconds is not None:
        params["ex"] = str(ex_seconds)

    response = requests.post(url, headers=kv_headers(), params=params, timeout=10)
    response.raise_for_status()


def seconds_until_day_end(now_utc):
    tomorrow = (now_utc + timedelta(days=1)).date()
    end_of_day = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)
    return int((end_of_day - now_utc).total_seconds())


def send_email(sender, password, receiver):
    subject = random.choice(SUBJECTS)
    body = random.choice(BODIES)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()

    return subject


def run_warmup():
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST not set")
    if not SMTP_PORT:
        raise RuntimeError("SMTP_PORT not set")
    if not MAIL1 or not PASS1 or not MAIL2 or not PASS2:
        raise RuntimeError("MAIL1/PASS1/MAIL2/PASS2 not set")

    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")

    count_key = f"warmup:count:{today_key}"
    last_key = "warmup:last_sent"

    last_sent_raw = kv_get(last_key)
    if last_sent_raw:
        try:
            last_sent = int(last_sent_raw)
            if int(now.timestamp()) - last_sent < MIN_INTERVAL_SECONDS:
                logging.info("Min interval not reached. Skipping.")
                return {
                    "status": "skipped",
                    "reason": "min_interval_not_reached",
                    "last_sent": last_sent,
                }
        except ValueError:
            logging.warning("Invalid last_sent in KV: %s", last_sent_raw)

    count_raw = kv_get(count_key)
    sent_today = int(count_raw) if count_raw else 0

    if sent_today >= DAILY_LIMIT:
        logging.info("Daily limit reached (%s). Skipping.", DAILY_LIMIT)
        return {"status": "skipped", "reason": "daily_limit_reached", "sent_today": sent_today}

    if random.choice([True, False]):
        subject = send_email(MAIL1, PASS1, MAIL2)
        sender = MAIL1
        receiver = MAIL2
    else:
        subject = send_email(MAIL2, PASS2, MAIL1)
        sender = MAIL2
        receiver = MAIL1

    sent_today += 1
    ttl = seconds_until_day_end(now)
    kv_set(count_key, sent_today, ex_seconds=ttl)
    kv_set(last_key, int(now.timestamp()), ex_seconds=ttl)

    logging.info(
        "SUCCESS | %s -> %s | Subject: %s | Sent Today: %s/%s",
        sender,
        receiver,
        subject,
        sent_today,
        DAILY_LIMIT,
    )

    return {
        "status": "sent",
        "subject": subject,
        "sender": sender,
        "receiver": receiver,
        "sent_today": sent_today,
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = run_warmup()
            body = json.dumps(result).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            logging.exception("Warmup failed")
            body = json.dumps({"status": "error", "message": str(exc)}).encode("utf-8")
            self.send_response(500)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    try:
        result = run_warmup()
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
