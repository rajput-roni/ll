import os
import time
import sqlite3
import requests
from threading import Thread
from queue import Queue
from serial import Serial

# GSM Module Configuration
GSM_PORT = '/dev/ttyUSB0'  # Change as per your device
BAUD_RATE = 9600

def send_sms_via_gsm(phone_number, message):
    try:
        ser = Serial(GSM_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)
        ser.write(b'AT\r\n')
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r\n')  # Set SMS mode to text
        time.sleep(1)
        ser.write(f'AT+CMGS="{phone_number}"
'.encode())
        time.sleep(1)
        ser.write(f'{message}\x1A'.encode())  # Ctrl+Z to send SMS
        time.sleep(3)
        ser.close()
        return True
    except Exception as e:
        print(f"GSM SMS Error: {e}")
        return False

# SQLite Database for Offline Storage
conn = sqlite3.connect('messages.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, message TEXT, status TEXT)''')
conn.commit()

def save_message(recipient, message):
    cursor.execute("INSERT INTO messages (recipient, message, status) VALUES (?, ?, ?)", (recipient, message, 'pending'))
    conn.commit()

def get_pending_messages():
    cursor.execute("SELECT * FROM messages WHERE status='pending'")
    return cursor.fetchall()

def update_message_status(message_id, status):
    cursor.execute("UPDATE messages SET status=? WHERE id=?", (status, message_id))
    conn.commit()

def send_message(recipient, message):
    if is_internet_available():
        send_via_facebook_messenger(recipient, message)
    else:
        send_sms_via_gsm(recipient, message)

def is_internet_available():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def send_via_facebook_messenger(recipient, message):
    token = "YOUR_FACEBOOK_ACCESS_TOKEN"
    url = f"https://graph.facebook.com/v12.0/me/messages?access_token={token}"
    payload = {
        "recipient": {"id": recipient},
        "message": {"text": message}
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"Facebook Messenger Error: {e}")
    return False

def process_pending_messages():
    while True:
        for msg in get_pending_messages():
            msg_id, recipient, message, status = msg
            if send_message(recipient, message):
                update_message_status(msg_id, 'sent')
        time.sleep(10)  # Retry every 10 seconds

Thread(target=process_pending_messages, daemon=True).start()

# Example Usage
if __name__ == "__main__":
    recipient = input("Enter recipient ID or phone number: ")
    message = input("Enter message: ")
    save_message(recipient, message)
    print("Message added to queue.")
