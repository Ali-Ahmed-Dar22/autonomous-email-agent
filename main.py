import base64
import re
import requests
from email.message import EmailMessage
from datetime import datetime
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
if  not  os.path.exists("token.json"):
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("✅ token.json created successfully")

# =========================
# CONFIG
# =========================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"  # your downloaded Gemma3 4B model

MAX_EMAILS_PER_RUN = 5  # limit per run
MANUAL_APPROVAL = True  # Set True to approve each reply before sending

SKIP_KEYWORDS = [
    "security alert",
    "verify",
    "suspicious",
    "login attempt",
    "password",
    "no-reply",
    "noreply@",
    "donotreply@",
]

LOG_FILE = "email_bot_log.txt"

# =========================
# UTILITY FUNCTIONS
# =========================
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

# =========================
# OLLAMA AI REPLY
# =========================
def check_ollama_status():
    try:
        response = requests.get("http://localhost:11434/")
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False

def generate_ai_reply(email_body):
    # Truncate email body to avoid excessively long prompts causing timeouts
    email_body = email_body[:3000] if email_body else ""
    
    prompt = f"""
You are a professional business assistant.
Reply politely, clearly, and concisely.
Do NOT mention AI.

Email:
\"\"\"{email_body}\"\"\"

Write a professional reply.
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )
        data = response.json()
        if "error" in data:
            log(f"⚠️ Ollama API Error: {data['error']}")
            return None
        return data.get("response", "").strip()
    except Exception as e:
        log(f"⚠️ Ollama connection error: {e}")
        return None

# =========================
# GMAIL HELPERS
# =========================
def get_gmail_service():
    creds = Credentials.from_authorized_user_file(
        "token.json", ["https://www.googleapis.com/auth/gmail.modify"]
    )
    return build("gmail", "v1", credentials=creds)

def get_unread_emails(service, max_results):
    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results
    ).execute()
    return result.get("messages", [])

def get_email_content(service, msg_id):
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = msg["payload"]["headers"]
    subject = sender = ""

    for h in headers:
        if h["name"] == "Subject":
            subject = h["value"]
        if h["name"] == "From":
            sender = h["value"]

    def extract_text(payload):
        if payload.get("mimeType") == "text/plain":
            if "data" in payload.get("body", {}):
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if "parts" in payload:
            for part in payload["parts"]:
                part_text = extract_text(part)
                if part_text:
                    return part_text
        return ""

    body = extract_text(msg.get("payload", {}))

    return subject, sender, body

def send_reply(service, to, subject, body, thread_id):
    message = EmailMessage()
    message.set_content(body)
    message["To"] = to
    message["Subject"] = "Re: " + subject

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(
            userId="me",
            body={
                "raw": encoded,
                "threadId": thread_id
            }
        ).execute()
        log(f"✅ Replied to {to} | Subject: {subject}")
    except Exception as e:
        log(f"⚠️ Failed to send email to {to}: {e}")

def mark_as_read(service, msg_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:
        log(f"⚠️ Failed to mark email {msg_id} as read: {e}")

# =========================
# SAFETY FILTER
# =========================
def should_skip(sender, subject):
    text = (sender + subject).lower()
    for kw in SKIP_KEYWORDS:
        if kw in text:
            return True
    return False

# =========================
# MAIN FUNCTION
# =========================
import time

def main():
    if not check_ollama_status():
        log("❌ Error: Ollama server is not running. Please start Ollama before running this script.")
        return

    service = get_gmail_service()
    
    # Check frequency in seconds
    POLL_INTERVAL = 60  
    log(f"🚀 Email Bot started! Monitoring inbox every {POLL_INTERVAL} seconds...")

    while True:
        try:
            messages = get_unread_emails(service, MAX_EMAILS_PER_RUN)

            if messages:
                log(f"\n📨 Unread Emails Found: {len(messages)}\n")

                for msg in messages:
                    msg_id = msg["id"]
                    subject, sender, body = get_email_content(service, msg_id)

                    log(f"📩 FROM: {sender}")
                    log(f"📝 SUBJECT: {subject}")

                    if should_skip(sender, subject):
                        log("⏭️ Skipped (system / security / no-reply)\n")
                        mark_as_read(service, msg_id)
                        continue

                    reply = generate_ai_reply(body)
                    if not reply:
                        log("⚠️ No reply generated\n")
                        continue

                    if MANUAL_APPROVAL:
                        log(f"\n--- Generated Reply ---\n{reply}\n----------------------")
                        approve = input("Send this reply? (y/n): ").strip().lower()
                        if approve != "y":
                            log("⏸️ Skipped sending\n")
                            continue

                    send_reply(service, sender, subject, reply, msg_id)
                    mark_as_read(service, msg_id)
            
            # Wait before checking again
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            log(f"⚠️ Error in main loop: {e}")
            # Wait a bit before retrying on error to avoid spamming the API
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
