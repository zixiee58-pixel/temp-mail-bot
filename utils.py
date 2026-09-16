import requests
import random
import base64
import re
import string
from datetime import datetime, timezone, timedelta

Token = "သင့်_Bot_Token_ကို_ဒီနေရာမှာ_ထည့်ပါ"

def Decode_MIME(mime_message: str) -> str:
    try:
        base64_parts = re.findall(
            r'Content-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: base64\r\n\r\n(.*?)\r\n--',
            mime_message,
            re.DOTALL
        )
        decoded_parts = []
        for part in base64_parts:
            decoded_part = base64.b64decode(part).decode('utf-8', errors='ignore')
            plain_text_part = re.sub(r'<.*?>', '', decoded_part)
            decoded_parts.append(plain_text_part)
        return "\n".join(decoded_parts)
    except Exception:
        return "Could not decode message."

def Get_Domains() -> list:
    try:
        response = requests.get("https://api.mail.tm/domains", timeout=15)
        if response.status_code == 200:
            return [domain["domain"] for domain in response.json()["hydra:member"]]
    except Exception:
        pass
    return ["mail.tm"]

def Create_Account(address: str, password: str) -> tuple:
    try:
        response = requests.post(
            "https://api.mail.tm/accounts",
            json={"address": address, "password": password},
            timeout=15
        )
        if response.status_code == 201:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)

def Login_Account(address: str, password: str) -> tuple:
    try:
        response = requests.post(
            "https://api.mail.tm/token",
            json={"address": address, "password": password},
            timeout=15
        )
        if response.status_code == 200:
            return True, response.json()["token"]
        return False, response.text
    except Exception as e:
        return False, str(e)

def Delete_Account(token: str) -> tuple:
    try:
        response = requests.delete(
            "https://api.mail.tm/accounts/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if response.status_code == 204:
            return True, "Deleted"
        return False, response.text
    except Exception as e:
        return False, str(e)

def Load_Mail_Box(token: str) -> tuple:
    try:
        response = requests.get(
            "https://api.mail.tm/messages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if response.status_code != 200:
            return False, f"API Error: {response.status_code}"
            
        messages = response.json()
        inboxes = []
        for message in messages.get("hydra:member", []):
            message_from = f"From: {message['from']['address']}\n"
            message_subj = f"Subject: {message['subject']}\n"
            message_intr = f"Intro: {message['intro']}\n"
            
            message_time = message.get('createdAt', 'Unknown time')
            try:
                dt = datetime.fromisoformat(message_time)
                mmt = timezone(timedelta(hours=6, minutes=30))
                dt = dt.astimezone(mmt)
                message_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            
            inboxes.append(f"🕒 {message_time}\n" + message_from + message_subj + message_intr)
            
        return True, inboxes
    except Exception as e:
        return False, f"An error occurred: {str(e)}"

def Generate_Email(address=None, password=None):
    domains = Get_Domains()
    if not domains:
        return False, "No domains available"
    domain = random.choice(domains)
    if not address:
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{username}@{domain}"
    if not password:
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    success, response = Create_Account(address, password)
    if not success:
        return False, response
        
    success, token = Login_Account(address, password)
    if not success:
        return False, token
        
    return True, [address, password, token]
