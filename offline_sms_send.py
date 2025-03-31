#!/usr/bin/python3
#-*-coding:utf-8-*-

"""
Offline GSM SMS Sender Script

Is script ko aap bina internet ke chalakar GSM module (SIM800L/SIM900A) ke through
direct SMS bhejne ke liye use kar sakte hain.
Ensure karein ki:
  - GSM module sahi tarah se connect ho (default serial port: /dev/ttyUSB0, baudrate: 115200)
  - Message file (plain text) available ho jismein har line ek alag SMS message ho.
  - Agar background mein chalana ho, to daemonize() function ko uncomment kar sakte hain.
"""

import os, sys, time, random, string, threading, sqlite3, datetime, warnings
from time import sleep
from platform import system

# Suppress DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- Daemonize Function (Background Mode) ---
def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except Exception:
        pass
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except Exception:
        pass
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

# --- SQLite DB for Logging Sent SMS ---
DB_NAME = 'sms_log.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def log_sent_message(phone, message):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO sent_messages (phone, message) VALUES (?, ?)", (phone, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Logging error:", e)

# --- GSM SMS Sending Function ---
def send_sms_via_gsm(phone, message):
    try:
        # pyserial module check
        try:
            import serial
        except ImportError:
            os.system("pip install pyserial")
            import serial

        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        # Initial handshake
        ser.write(b'AT\r')
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        cmd = f'AT+CMGS="{phone}"\r'
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        ser.write(bytes([26]))  # Ctrl+Z signal
        time.sleep(3)
        response = ser.read_all().decode()
        ser.close()
        if "OK" in response:
            return True
        else:
            return False
    except Exception as e:
        print("Error in sending SMS:", e)
        return False

# --- Function to Display Sent Messages Log ---
def display_sent_messages():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT phone, message, timestamp FROM sent_messages ORDER BY timestamp")
        rows = c.fetchall()
        conn.close()
        if not rows:
            print("Koi sent message nahi mila.")
            return
        print("=" * 70)
        for phone, message, ts in rows:
            print(f"[{ts}] To: {phone}\nMessage: {message}\n" + "-" * 70)
    except Exception as e:
        print("Error displaying log:", e)

# --- Check Stop Signal ---
def check_stop():
    if os.path.exists("stop_signal.txt"):
        sys.exit()

# --- SMS Sending Loop Function ---
def send_sms_loop(phone, message_lines, repeat, delay_sec):
    sms_count = 0
    while True:
        check_stop()
        for line in message_lines:
            line = line.strip()
            if not line:
                continue
            full_message = line
            if send_sms_via_gsm(phone, full_message):
                sms_count += 1
                now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                print(f"[{now}] SMS #{sms_count} sent to {phone}:\n{full_message}\n")
                log_sent_message(phone, full_message)
            else:
                print("SMS bhejne mein error. 30 seconds baad retry karenge...")
                time.sleep(30)
            time.sleep(delay_sec)
        if repeat == 0:  # 0 ka matlab infinite repetition
            continue
        else:
            repeat -= 1
            if repeat <= 0:
                break

# --- Utility Function to Clear Screen ---
def cls():
    if system() == 'Linux':
        os.system('clear')
    elif system() == 'Windows':
        os.system('cls')

# --- Main Menu ---
def main_menu():
    print("=" * 50)
    print("Offline GSM SMS Sender")
    print("=" * 50)
    print("[1] SMS bhejna shuru karein")
    print("[2] Sent messages log dekhain")
    print("[3] Script ko band karein")
    choice = input("Apni choice likhein: ").strip()
    return choice

# --- Main Execution ---
def main():
    cls()
    choice = main_menu()
    if choice == "2":
        display_sent_messages()
        sys.exit()
    if choice == "3":
        with open("stop_signal.txt", "w") as f:
            f.write("stop")
        print("Script band kar diya gaya.")
        sys.exit()
    if choice != "1":
        print("Galat choice. Exiting.")
        sys.exit()

    # Input parameters
    phone = input("Target phone number (country code ke saath, jaise +919XXXXXXXXX): ").strip()
    message_file = input("Message file ka naam (txt file): ").strip()
    if not os.path.exists(message_file):
        print("Error: Message file maujood nahin hai.")
        sys.exit(1)
    try:
        repeat = int(input("Repeat count (0 agar infinite): ").strip())
    except:
        repeat = 1
    try:
        delay_sec = int(input("SMS bhejne ka delay (seconds mein): ").strip())
    except:
        delay_sec = 10

    with open(message_file, 'r', encoding='utf-8') as f:
        message_lines = f.readlines()
    if not message_lines:
        print("Error: Message file khaali hai.")
        sys.exit(1)

    print(f"SMS bhejne ke liye shuru ho raha hai: {phone}")
    # Agar aap background mein run karna chahte hain, to neeche wali line ko uncomment kar dein
    # daemonize()
    send_sms_loop(phone, message_lines, repeat, delay_sec)

if __name__ == "__main__":
    main()
