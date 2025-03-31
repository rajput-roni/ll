#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
IMPORTANT:
- यह script interactive इनपुट लेने के बाद daemonize (background में detach) हो जाती है,
  ताकि Termux exit होने के बाद भी SMS भेजती रहे – चाहे इंटरनेट/मोबाइल off हो।
- GSM SMS fallback के लिए GSM मॉड्यूल (जैसे SIM800L/SIM900A) कनेक्ट होना चाहिए, और उसका 
  serial port (default: /dev/ttyUSB0) एवं baudrate (115200) सही से सेट हों।
- Token file में प्रत्येक लाइन पर एक valid token होना चाहिए।
"""

import os, sys, time, random, string, requests, json, threading, sqlite3, datetime, warnings
from time import sleep
from platform import system

# Suppress DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Global flags
DEBUG = True

# --- Import pyserial and colorama ---
try:
    import serial
except ImportError:
    os.system("pip install pyserial")
    import serial

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    os.system("pip install colorama")
    from colorama import Fore, Style, init
    init(autoreset=True)

requests.urllib3.disable_warnings()

# --- Daemonize Function ---
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
    with open(os.devnull, 'r') as si, open(os.devnull, 'a+') as so, open(os.devnull, 'a+') as se:
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

# --- SQLite3 DB Integration for offline message queue and logging ---
DB_NAME = 'message_queue.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            hater_name TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_to_queue(thread_id, message):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO message_queue (thread_id, message) VALUES (?, ?)", (thread_id, message))
        conn.commit()
        conn.close()
        print(Fore.YELLOW + "[•] Message added to offline queue.")
    except Exception as e:
        if DEBUG:
            print("Error adding to queue:", e)

def get_pending_messages():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, thread_id, message FROM message_queue WHERE status = 'pending'")
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        if DEBUG:
            print("Error fetching pending messages:", e)
        return []

def mark_message_sent(message_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE message_queue SET status = 'sent' WHERE id = ?", (message_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        if DEBUG:
            print("Error marking message as sent:", e)

def log_sent_message(thread_id, hater_name, message):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO sent_messages (thread_id, hater_name, message) VALUES (?, ?, ?)",
                  (thread_id, hater_name, message))
        conn.commit()
        conn.close()
    except Exception as e:
        if DEBUG:
            print("Error logging sent message:", e)

# --- Helper function for random ANSI color ---
def get_random_color():
    colors = [
        "\033[1;31m", "\033[1;32m", "\033[1;33m",
        "\033[1;34m", "\033[1;35m", "\033[1;36m", "\033[1;37m"
    ]
    return random.choice(colors)

# --- Function to print SMS send section ---
def print_sms_section(msg_index, sender, target, thread_id, full_message, timestamp):
    border = f"{get_random_color()}<<{'='*75}>>{Style.RESET_ALL}"
    print(border)
    print(f"{get_random_color()}[#{msg_index}] SENT by {sender} to {target} ({thread_id})")
    print(f"{get_random_color()}Message: {full_message}")
    print(f"{get_random_color()}Time: {timestamp}{Style.RESET_ALL}")
    print(border)

# --- Connectivity Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

# --- GSM SMS Sending via GSM module ---
def send_sms_via_gsm(phone, message):
    try:
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        ser.write(b'AT\r')
        time.sleep(1)
        resp1 = ser.read_all().decode()
        if DEBUG:
            print("Response AT:", resp1)
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        resp2 = ser.read_all().decode()
        if DEBUG:
            print("Response AT+CMGF=1:", resp2)
        cmd = f'AT+CMGS="{phone}"\r'
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        ser.write(bytes([26]))  # Ctrl+Z to send SMS
        time.sleep(3)
        response = ser.read_all().decode()
        if DEBUG:
            print("Response for SMS:", response)
        ser.close()
        if "OK" in response:
            return True
        else:
            return False
    except Exception as e:
        if DEBUG:
            print("Exception in send_sms_via_gsm:", e)
        return False

# --- Background Offline Queue Processor ---
def process_queue():
    global global_token_index, tokens, fallback_phone, mn
    while True:
        check_stop()
        pending = get_pending_messages()
        for row in pending:
            msg_id, t_id, msg = row
            if is_connected():
                # Try sending using Facebook API (not covered in detail here)
                current_token = tokens[global_token_index]
                global_token_index = (global_token_index + 1) % len(tokens)
                url = f"https://graph.facebook.com/v15.0/t_{t_id}/"
                parameters = {'access_token': current_token, 'message': msg}
                try:
                    s = requests.post(url, data=parameters)
                    if s.ok:
                        mark_message_sent(msg_id)
                        log_sent_message(t_id, mn, msg)
                    else:
                        try:
                            resp = s.json()
                            if 'error' in resp and resp['error'].get('code') == 190:
                                print(Fore.RED + f"[!] Token expired in queue: {current_token[:10]}... Skipping token.")
                                continue
                        except:
                            pass
                except:
                    pass
            else:
                if send_sms_via_gsm(fallback_phone, msg):
                    mark_message_sent(msg_id)
                    log_sent_message(t_id, mn, msg)
        time.sleep(10)

def start_queue_processor():
    t = threading.Thread(target=process_queue, daemon=True)
    t.start()

# --- Utility to check for stop signal ---
def check_stop():
    if os.path.exists("stop_signal.txt"):
        sys.exit()

# --- Basic UI functions for demonstration (can be customized) ---
def cls():
    if system() == 'Linux':
        os.system('clear')
    elif system() == 'Windows':
        os.system('cls')

def main_menu():
    print(Fore.CYAN + "=== Offline SMS Sender Menu ===" + Style.RESET_ALL)
    print("[1] Start SMS Loader")
    print("[2] Stop Loader")
    print("[3] Show Sent Messages")
    choice = input("Choose an option (or enter STOP key): ").strip()
    if choice == "2":
        stop_key = input("Enter STOP key: ").strip()
        if stop_key == get_stop_key():
            with open("stop_signal.txt", "w") as f:
                f.write("stop")
            sys.exit()
    if choice == "3":
        display_sent_messages()
        sys.exit()
    return choice

def get_stop_key():
    if os.path.exists("loader_stop_key.txt"):
        with open("loader_stop_key.txt", "r") as f:
            return f.read().strip()
    else:
        stop_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        with open("loader_stop_key.txt", "w") as f:
            f.write(stop_key)
        return stop_key

# --- Dummy function to simulate sending SMS via Facebook API ---
# यदि इंटरनेट उपलब्ध हो तो Facebook API से मैसेज भेजेगा, अन्यथा GSM fallback का उपयोग होगा।
def message_on_messenger(thread_id):
    global global_token_index, tokens, fallback_phone, ns, mn, message_index
    try:
        uid_val = os.getuid()
    except:
        uid_val = "N/A"
    for line in ns:
        check_stop()
        full_message = f"{mn} {line.strip()}"
        if is_connected():
            current_token = tokens[global_token_index]
            global_token_index = (global_token_index + 1) % len(tokens)
            url = f"https://graph.facebook.com/v15.0/t_{thread_id}/"
            parameters = {'access_token': current_token, 'message': full_message}
            try:
                s = requests.post(url, data=parameters)
                if s.ok:
                    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                    print_sms_section(message_index+1, mn, "FB Messenger", thread_id, full_message, now)
                    message_index += 1
                    log_sent_message(thread_id, mn, full_message)
                else:
                    time.sleep(30)
            except:
                time.sleep(30)
        else:
            if send_sms_via_gsm(fallback_phone, full_message):
                now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                print_sms_section(message_index+1, mn, "GSM SMS", thread_id, full_message, now)
                message_index += 1
                log_sent_message(thread_id, mn, full_message)
            else:
                add_to_queue(thread_id, full_message)

# --- Main Execution ---
cls()
if os.path.exists("stop_signal.txt"):
    os.remove("stop_signal.txt")

# Display a basic banner
print(Fore.GREEN + "Offline SMS Sender with GSM Fallback" + Style.RESET_ALL)
print(Fore.GREEN + "Starting at:", datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p") + Style.RESET_ALL)

menu_choice = main_menu()
if menu_choice != "1":
    sys.exit()

# Simulate interactive inputs
token_file = input("[+] Enter Token File Name: ").strip()
if not os.path.exists(token_file):
    print(Fore.RED + "Token file does not exist." + Style.RESET_ALL)
    sys.exit(1)

with open(token_file, 'r') as f:
    token_data = f.read()
all_tokens = [line.strip() for line in token_data.splitlines() if line.strip()]
if not all_tokens:
    print(Fore.RED + "No valid tokens found." + Style.RESET_ALL)
    sys.exit(1)

active_tokens = []
active_token_profiles = []
expired_tokens = []
def fetch_profile_name(token):
    try:
        payload = {'access_token': token}
        r = requests.get("https://graph.facebook.com/v15.0/me", params=payload)
        data = r.json()
        return data.get('name', "Invalid Token")
    except:
        return "Error"

for token in all_tokens:
    profile = fetch_profile_name(token)
    if profile not in ["Invalid Token", "Error"]:
        active_tokens.append(token)
        active_token_profiles.append((token, profile, get_random_color()))
    else:
        expired_tokens.append(token)

if not active_tokens:
    print(Fore.RED + "No active tokens found." + Style.RESET_ALL)
    sys.exit(1)

tokens = active_tokens
mn = active_token_profiles[0][1]
print(Fore.GREEN + "Your Profile Name: " + mn + Style.RESET_ALL)
print(Fore.CYAN + "Active Tokens:" + Style.RESET_ALL)
for idx, (token, profile, color) in enumerate(active_token_profiles, start=1):
    token_display = token if len(token) <= 20 else token[:20] + "..."
    print(color + f"{idx}. Token: {token_display} | Profile: {profile}" + Style.RESET_ALL)

fallback_phone = input("[+] Enter fallback GSM phone number (with country code): ").strip()
thread_id = input("[+] Enter Convo UID (or thread id): ").strip()
mn = input("[+] Enter Hater's Name: ").strip()
message_file = input("[+] Enter Message File Path: ").strip()

try:
    ns = open(message_file, 'r').readlines()
except:
    print(Fore.RED + "Message file not found." + Style.RESET_ALL)
    sys.exit(1)

repeat = int(input("[+] Enter file repeat count: ").strip())

# Start offline queue processor thread
start_queue_processor()

# If daemonize is desired, detach from terminal
daemonize()

# If multiple tokens, use separate threads; else, use single thread
if len(active_token_profiles) > 1:
    threads = []
    for token, profile, color in active_token_profiles:
         t = threading.Thread(target=message_on_messenger, args=(thread_id,), daemon=True)
         threads.append(t)
         t.start()
    for t in threads:
         t.join()
else:
    for i in range(repeat):
        check_stop()
        message_on_messenger(thread_id)
