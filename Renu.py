#!/usr/bin/python3
#-*-coding:utf-8-*-
"""
IMPORTANT:
- यह स्क्रिप्ट interactive इनपुट लेने के बाद अपने आप daemonize (background में detach) हो जाती है,
  ताकि Termux exit होने के बाद भी SMS भेजती रहे – चाहे इंटरनेट/मोबाइल off हो।
- GSM SMS fallback के लिए GSM मॉड्यूल (जैसे SIM800L/SIM900A) कनेक्ट होना चाहिए,
  और उसका serial port (default: /dev/ttyUSB0) एवं baudrate (115200) सही से सेट हों।
- Unlimited token support: टोकन फ़ाइल में हर टोकन एक नई लाइन में होना चाहिए।
- यह स्क्रिप्ट बिना बाहरी कमांड (nohup/tmux/screen आदि) के ही अपने अंदर ही daemonize हो जाती है,
  ताकि 1 साल तक लगातार चल सके (सही हार्डवेयर सपोर्ट के साथ)।
"""

import os, sys, time, random, string, re, requests, json, uuid
from concurrent.futures import ThreadPoolExecutor as ThreadPool
from platform import system
import datetime
from time import sleep
import sqlite3

# --- Additional module for GSM SMS fallback ---
try:
    import serial
except ImportError:
    print("pyserial not installed. Installing...")
    os.system("pip install pyserial")
    import serial

# --- Models Installer (includes pyserial) ---
def modelsInstaller():
    try:
        models = ['requests', 'colorama', 'pyserial']
        for model in models:
            try:
                if(sys.version_info[0] < 3):
                    os.system('cd C:\Python27\Scripts & pip install {}'.format(model))
                else:
                    os.system('python3 -m pip install {}'.format(model))
                print(' ')
                print('[+] {} has been installed successfully, Restart the program.'.format(model))
                sys.exit()
                print(' ')
            except:
                print('[-] Install {} manually.'.format(model))
                print(' ')
    except:
        pass

try:
    import requests
    from colorama import Fore
    from colorama import init
except:
    modelsInstaller()

requests.urllib3.disable_warnings()

# --- Daemonize Function ---
def daemonize():
    """Double-fork daemonization to detach the process from terminal."""
    try:
        pid = os.fork()
        if pid > 0:
            # Exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: {0}\n".format(e))
        sys.exit(1)
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0:
            # Exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: {0}\n".format(e))
        sys.exit(1)
    # Redirect standard file descriptors to /dev/null.
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

# --- SQLite3 DB Integration for Offline Message Queue ---
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
    conn.commit()
    conn.close()

def add_to_queue(thread_id, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO message_queue (thread_id, message) VALUES (?, ?)", (thread_id, message))
    conn.commit()
    conn.close()
    print("\033[1;33m[•] Internet/SMS not available. Message added to offline queue.")

def get_pending_messages():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, thread_id, message FROM message_queue WHERE status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return rows

def mark_message_sent(message_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE message_queue SET status = 'sent' WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

# --- Connectivity Check ---
def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# --- GSM SMS Sending via connected GSM module ---
def send_sms_via_gsm(phone, message):
    try:
        # Adjust port and baudrate as per your GSM module configuration
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        ser.write(b'AT\r')
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r')  # Set SMS Text Mode
        time.sleep(1)
        cmd = 'AT+CMGS="{}"\r'.format(phone)
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        ser.write(bytes([26]))  # CTRL+Z to send SMS
        time.sleep(3)
        response = ser.read_all().decode()
        ser.close()
        if "OK" in response:
            print("\033[1;32m[•] SMS sent successfully via GSM module.")
            return True
        else:
            print("\033[1;31m[×] Failed to send SMS via GSM module. Response:", response)
            return False
    except Exception as e:
        print("\033[1;31m[×] Exception in send_sms_via_gsm:", e)
        return False

# --- Background Offline Queue Processor ---
def process_queue():
    global global_token_index, tokens, fallback_phone
    while True:
        pending = get_pending_messages()
        for row in pending:
            msg_id, t_id, msg = row
            if is_connected():
                # Use Facebook API sending with round-robin token selection
                current_token = tokens[global_token_index]
                global_token_index = (global_token_index + 1) % len(tokens)
                url = "https://graph.facebook.com/v15.0/{0}/".format('t_' + str(t_id))
                parameters = {'access_token': current_token, 'message': msg}
                try:
                    s = requests.post(url, data=parameters, headers=headers)
                    if s.ok:
                        print("\033[1;32m[•] Queued message sent successfully via FB API.")
                        mark_message_sent(msg_id)
                    else:
                        print("\033[1;31m[×] Failed to send queued message via FB API, will retry.")
                except Exception as e:
                    print("\033[1;31m[×] Exception sending queued message via FB API:", e)
            else:
                # No Internet: attempt GSM SMS sending
                if send_sms_via_gsm(fallback_phone, msg):
                    print("\033[1;32m[•] Queued SMS sent successfully via GSM module.")
                    mark_message_sent(msg_id)
                else:
                    print("\033[1;31m[×] Queued SMS send failed, will retry.")
        time.sleep(10)

import threading
def start_queue_processor():
    t = threading.Thread(target=process_queue, daemon=True)
    t.start()

# --- Initialize the offline DB ---
init_db()

def testPY():
    if(sys.version_info[0] < 3):
        print('\n\t [+] You have Python 2, Please Clear Data Termux And Reinstall Python ... \n')
        sys.exit()

def cls():
    if system() == 'Linux':
        os.system('clear')
    elif system() == 'Windows':
        os.system('cls')

cls()
CLEAR_SCREEN = '\033[2J'
RED = '\033[1;37;1m'
RESET = '\033[1;37;1m'
BLUE = "\033[1;37;1m"
WHITE = "\033[1;37;1m"
YELLOW = "\033[1;37;1m"
CYAN = "\033[1;37;1m"
MAGENTA = "\033[1;37;1m"
GREEN = "\033[1;37;1m"
BOLD = '\033[1;37;1m'
REVERSE = "\033[1;37;1m"

def logo():
    clear = "\x1b[0m"
    colors = [35, 33, 36]
    x = """   
    
\033[1;36m$$$$$$$\   $$$$$$\     $$$$$\ 
\033[1;36m$$  __$$\ $$  __$$\    \__$$ |
\033[1;34m$$ |  $$ |$$ /  $$ |      $$ |
\033[1;34m$$$$$$$  |$$$$$$$$ |      $$ |
\033[1;36m$$  __$$< $$  __$$ |$$\   $$ |
\033[1;32m$$ |  $$ |$$ |  $$ |$$ |  $$ |
\033[1;33m$$ |  $$ |$$ |  $$ |\$$$$$$  |
\033[1;33m\__|  \__|\__|  \__| \______/ 
                                           
                                                    
"""
    for N, line in enumerate(x.split("\n")):
        sys.stdout.write("\x1b[1;%dm%s%s\n" % (random.choice(colors), line, clear))
        time.sleep(0.07)
        
def menu3():
    try:
        uid = os.getuid()  # auto key generated by Termux uid
        xx = 'libsooney.so'
        try:
            key1 = open(f'/data/data/com.termux/files/usr/bin/{xx}', 'r').read()
        except:
            key1 = "default_key"
            open(f'/data/data/com.termux/files/usr/bin/{xx}', 'w').write(key1)
        key1 = open(f'/data/data/com.termux/files/usr/bin/{xx}', 'r').read()
        key = f'RAJ-XD-YWR-APRUAL-DO{uid}5X{key1}110E=='  # full key
        mysite = requests.get(f'').text  # approve site URL (if any)
        if key in mysite:
            print(logo)
            print('[+] Congratulations! You are a Premium User...'); time.sleep(2)
            print(logo)
            os.system('espeak -a 300 "well,come to, शर्मा डी स्टोन, tools"')
            print(f"""\x1b[1;97m 
\033[1;36m$$$$$$$\   $$$$$$\     $$$$$\ 
\033[1;36m$$  __$$\ $$  __$$\    \__$$ |
\033[1;34m$$ |  $$ |$$ /  $$ |      $$ |
\033[1;34m$$$$$$$  |$$$$$$$$ |      $$ |
\033[1;36m$$  __$$< $$  __$$ |$$\   $$ |
\033[1;32m$$ |  $$ |$$ |  $$ |$$ |  $$ |
\033[1;33m$$ |  $$ |$$ |  $$ |\$$$$$$  |
\033[1;33m\__|  \__|\__|  \__| \______/ 
                                           
\x1b[1;30m════════════════════════════════════════════════════════
\033[1;31m▇==➤ ADMIN       : RAJ-THAKUR L3G3ND
\033[1;37m▇==➤ GITHUB      : RAJ-THAKUR L3G3ND
\033[1;31m▇==➤ CREATOR    : RAJ-TH3-L3G3ND-BOY
\033[1;37m▇==➤ FACEBOOK   : OPS PHD RAJ-THAKUR
\x1b[1;30m════════════════════════════════════════════════════════
\033[1;33m[•] 01  START TOOL ADD FB ID\033[1;36m
\033[1;32m[•] 02  START TOOL TOKAN CONVO\033[1;36m
\033[1;30m[•] 00  EXIT TOOL \033[1;36m

════════════════════════════════════════════════════════""")
            os.system('espeak -a 300 "OFSAN CHUNE ONE YA TWO YA ZERO"')
            key_input = input("[+] Choose : ")                
            if key_input in [""]:
                print("(×) Please Select Correct Option")
                logo()
            elif key_input in ["1","01"]:
                os.system("am start https://www.facebook.com/profile.php?id=100068926301329" + key_input)                
            elif key_input in ["0","00","E","e"]:
                sys.exit('\033[1;32m[>] Thank You ')
            else:
                print('[×] Choose Correct Option'); time.sleep(1)
        else:
            print(logo)
            print('[•] Your Key Not Registered...')
            print('[•] This Tool is Only For Paid Users \n[•] Free Users Stay Away')
            os.system('espeak -a 300 "well,come to, RAJ THAKUR G4W4R, tools"')
            print('[•] Your Key : ' + key)
            os.system("am start https://wa.me/+919695003501?text=" + key)
            input('[] Press Enter For Approval ')    
            whatsapp = "+919695003501"
            url_wa = "https://api.whatsapp.com/send?phone=" + whatsapp + "&text="
            tks = ("Hello Raj Thakur boss, I Need To Buy Your Paid Tools. Please Approve My Key :)\n\n Key :- " + key)
            import subprocess
            subprocess.check_output(["am", "start", url_wa + (tks)]); time.sleep(2)
            print('Run : python RIAZ.py'); 
    except ValueError:
        pass

menu3()        
testPY()
print('\033[1;33m════════════════════════════════════════════════════════\n')

def venom():
    clear = "\x1b[0m"
    colors = [35, 33, 36]
    y = '''
\033[1;33m════════════════════════════════════════════════════════
\033[1;31m N4ME    \033[1;34m: \033[1;33mRAJ H3R3 |=|_|
\033[1;36m CrEaToR  \033[1;35m: \033[1;34mL3G3ND RAJ                      
\033[1;31m OWN3R   \033[1;36m: \033[1;35mOPS RAJ DON
\033[1;36m Contact \033[1;33m: \033[1;36m+919695003501
\033[1;33m════════════════════════════════════════════════════════
'''
    for N, line in enumerate(y.split("\n")):
        sys.stdout.write("\x1b[1;%dm%s%s\n" % (random.choice(colors), line, clear))
        time.sleep(0.05)
    	
venom()

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

# --- Global Variables for Unlimited Token Support & GSM fallback ---
global_token_index = 0
tokens = []       # To be filled from token file
fallback_phone = ""  # Fallback phone number for SMS (with country code)

# --- Modified Message Sending Function ---
def message_on_messenger(thread_id):
    global global_token_index, tokens, fallback_phone
    for line in ns:
        full_message = str(mn) + line
        if is_connected():
            # Use round-robin token selection for FB API
            current_token = tokens[global_token_index]
            global_token_index = (global_token_index + 1) % len(tokens)
            url = "https://graph.facebook.com/v15.0/{0}/".format('t_' + str(thread_id))
            parameters = {'access_token': current_token, 'message': full_message}
            try:
                s = requests.post(url, data=parameters, headers=headers)
                tt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                if s.ok:
                    e = datetime.datetime.now()
                    print('''\033[1;33m════════════════════════════════════════════════════════\n''')
                    print("\033[1;32;40m", end = "")
                    print("--> Convo/Inbox ID Link  :--", thread_id)
                    print(e.strftime("--> D4RIIND4 RAJ H3R3 :D | | Date :: %d-%m-%Y  TIME :: %I:%M:%S %p"))
                    print("--> Message Successfully Sent :-->> ", full_message, "\n")
                    print('''\033[1;33m════════════════════════════════════════════════════════\n''')
                    time.sleep(timm)
                else:
                    print('\033[1;32m[x] Message Block ' + tt, '\n[×] Token Error\n')
                    time.sleep(30)
            except Exception as e:
                print("\033[1;31;40m", end = "")
                print(e, '\n')           
                time.sleep(30)
        else:
            # No Internet: Attempt GSM SMS sending
            print("\033[1;33m[•] No Internet. Attempting to send SMS via GSM module...")
            if send_sms_via_gsm(fallback_phone, full_message):
                print("\033[1;32m[•] SMS sent via GSM module.")
            else:
                print("\033[1;31m[×] SMS sending via GSM failed. Adding message to offline queue.")
                add_to_queue(thread_id, full_message)

def get_messages():
    try:
        url = "https://www.facebook.com"
    except Exception as e:
        print("Error:", e)

# --- Main Execution Block ---
if True:    
    i = datetime.datetime.now()
    print(i.strftime("\033[1;32m[•] Start Time ==> %Y-%m-%d %I:%M:%S %p "))
    print('\033[1;32m[•] _ Tool Creator == > [ RAJ THAKUR KA LODA ON FIRE ♻️ ]\n')
    print("\033[1;36;40m", end = "")
    print(f"""\x1b[1;97m 
\033[1;36m$$$$$$$\   $$$$$$\     $$$$$\ 
\033[1;36m$$  __$$\ $$  __$$\    \__$$ |
\033[1;34m$$ |  $$ |$$ /  $$ |      $$ |
\033[1;34m$$$$$$$  |$$$$$$$$ |      $$ |
\033[1;36m$$  __$$< $$  __$$ |$$\   $$ |
\033[1;32m$$ |  $$ |$$ |  $$ |$$ |  $$ |
\033[1;33m$$ |  $$ |$$ |  $$ |\$$$$$$  |
\033[1;33m\__|  \__|\__|  \__| \______/ 


         \033[1;33m  /$$$$$$$   /$$$$$$  /$$$$$$$$ /$$   /$$  /$$$$$$  /$$   /$$
          \033[1;33m| $$__  $$ /$$__  $$|__  $$__/| $$  | $$ /$$__  $$| $$  /$$/
          \033[1;36m| $$  \ $$| $$  \ $$   | $$   | $$  | $$| $$  \ $$| $$ /$$/ 
          \033[1;36m| $$$$$$$/| $$$$$$$$   | $$   | $$$$$$$$| $$$$$$$$| $$$$$/  
          \033[1;33m| $$____/ | $$__  $$   | $$   | $$__  $$| $$__  $$| $$  $$  
          |\033[1;35m $$      | $$  | $$   | $$   | $$  | $$| $$  | $$| $$\  $$ 
          \033[1;36m| $$      | $$  | $$   | $$   | $$  | $$| $$  | $$| $$ \  $$
          \033[1;53m|__/      |__/  |__/   |__/   |__/  |__/|__/  |__/|__/  \__/
                                                            
                                                            
                                                            
                                           
\x1b[1;34m════════════════════════════════════════════════════════
\033[1;31m▇==➤ ADMIN        : RAJ-THAKUR
\033[1;37m▇==➤ GITHUB       : RAJ-THAKUR
\033[1;31m▇==➤ OWNER        : RAJ-THAKUR
\033[1;37m▇==➤ FACEBOOK     : L3G3NDCHOD R9J
\033[1;32m▇==➤ BROTHER      : RAJ THAKUR X3 DEV PANDIT
\x1b[1;34m════════════════════════════════════════════════════════""")
    os.system('espeak -a 300 "TOKAN FILE NAME DALO"')
    token_file = input("[+] Input Token File Name :: ")
    print('\n')
    with open(token_file, 'r') as f2:
        token_data = f2.read()
    tokens = [line.strip() for line in token_data.splitlines() if line.strip()]
    if len(tokens) == 0:
        print("No tokens found. Exiting.")
        sys.exit()
    access_token = tokens[0]  # For profile verification
    
    # Prompt for fallback phone number for SMS (include country code, e.g., +91XXXXXXXXXX)
    fallback_phone = input("[+] Enter fallback phone number for SMS (with country code): ").strip()
    
    payload = {'access_token': access_token}
    a = "https://graph.facebook.com/v15.0/me"
    b = requests.get(a, params=payload)
    d = json.loads(b.text)
    if 'name' not in d:
        print(BOLD + RED + '\n[x] Token Invalid..!!')
        sys.exit()
    mb = d['name']
    print('\033[1;32mYour Profile Name :: \033[1;32;1m%s' % (mb))
    print('\n')
    
    # Start background offline queue processor
    start_queue_processor()
    
    os.system('espeak -a 300 "CONVO ID DALO JAHA GALI DENI HA"')
    thread_id = input(BOLD + CYAN + "[+] Conversation ID :: ")
    os.system('espeak -a 300 "TATE KA NAME DALO"')
    mn = input(BOLD + CYAN + "[+] Enter Kidx Name :: ")
    os.system('espeak -a 300 "GALI FILE DALO"')
    ms = input(BOLD + CYAN + "[+] Add Gali File Name :: ")
    os.system('espeak -a 300 "FILE KITNI BAAR REPIT KARANI HA"')
    repeat = int(input(BOLD + CYAN + "[+] File Repeat No :: "))
    os.system('espeak -a 300 "SPEED DALO YAR"')
    timm = int(input(BOLD + CYAN + "[+] Speed in Seconds :: "))
    print('\n')
    print('\033[1;34m________All Done....Loading Profile Info.....!')
    print('\033[1;34mYour Profile Name :: ', mb)
    print('\n')
    ns = open(ms, 'r').readlines()
    
    # ----- Daemonize now so that the script runs in background even after Termux exit -----
    daemonize()
    
    # Main loop: send messages repeatedly as per the input repeat count
    for i in range(repeat):
        get_messages()  # For compatibility; can be expanded if needed.
        message_on_messenger(thread_id)
else:
    print(BOLD + RED + '[-] <==> Your Number Is Wrong Please Take Approval From Owner')
