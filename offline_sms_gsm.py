#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Offline SMS Sender using GSM Module (SIM800L/SIM900A)

Yeh script GSM module se bina internet ke SMS bhejne ke liye hai.
Aapko serial port, baud rate, recipient phone number, aur message as command-line arguments pass karne honge.
Agar aap background (daemon) mein run karna chahte hain, toh --daemonize flag ka use karein.
"""

import os
import sys
import time
import argparse
import warnings

# Suppress DeprecationWarnings (e.g. from os.fork())
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    import serial
except ImportError:
    os.system("pip install pyserial")
    import serial

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

# --- GSM SMS Sending Function ---
def send_sms_via_gsm(port, baud, phone, message):
    try:
        # Connect to GSM module
        ser = serial.Serial(port, baud, timeout=5)
        time.sleep(1)
        print("Connected to GSM module on port:", port)
        
        # Send AT command to check connection
        ser.write(b'AT\r')
        time.sleep(1)
        response = ser.read_all().decode()
        print("Response for AT command:", response)
        if "OK" not in response:
            print("GSM module ne sahi AT response nahi diya.")
            ser.close()
            return False

        # Set SMS text mode
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        response = ser.read_all().decode()
        print("Response for AT+CMGF=1:", response)
        
        # Prepare to send SMS
        cmd = 'AT+CMGS="{}"\r'.format(phone)
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        # Send CTRL+Z to indicate end of message
        ser.write(bytes([26]))
        time.sleep(3)
        response = ser.read_all().decode()
        print("Final response:", response)
        ser.close()

        if "OK" in response:
            print("SMS successfully bheji gayi!")
            return True
        else:
            print("SMS bhejne mein problem aayi.")
            return False
    except Exception as e:
        print("Error sending SMS via GSM:", e)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Offline SMS sender using GSM module (SIM800L/SIM900A) - bina internet ke SMS bheje"
    )
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0",
                        help="GSM module ka serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200,
                        help="GSM module ka baud rate (default: 115200)")
    parser.add_argument("--phone", type=str, required=True,
                        help="Recipient phone number (international format, e.g. +919453107259)")
    parser.add_argument("--message", type=str, required=True,
                        help="Bhejne wala message text")
    parser.add_argument("--daemonize", action="store_true",
                        help="Agar background mein run karna hai, toh is flag ka istemal karein")
    
    args = parser.parse_args()
    
    if args.daemonize:
        daemonize()
    
    print("SMS sending process shuru ho raha hai...")
    success = send_sms_via_gsm(args.port, args.baud, args.phone, args.message)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
