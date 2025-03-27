#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Offline SMS Sender Tool - renu.py
----------------------------------
यह स्क्रिप्ट बिना इंटरनेट के GSM मॉड्यूल (SIM800L/SIM900A) के जरिए SMS भेजती है।
इसका उद्देश्य Termux (Android) पर USB-to-TTL कनवर्टर के साथ GSM मॉड्यूल का उपयोग करना है।

हार्डवेयर सेटअप:
1. GSM मॉड्यूल (SIM800L/SIM900A) को निम्नलिखित तरीके से कनेक्ट करें:
   - VCC: 3.7V–4.2V वाले पावर स्रोत से कनेक्ट करें (सीधे 5V न दें)
   - GND: पावर स्रोत और USB-to-TTL कनवर्टर के GND से जोड़ें
   - TX: GSM मॉड्यूल का TX पिन → USB-to-TTL कनवर्टर के RX पिन से
   - RX: GSM मॉड्यूल का RX पिन → USB-to-TTL कनवर्टर के TX पिन से
2. USB-to-TTL कनवर्टर को OTG केबल के माध्यम से Android फोन (Termux) से कनेक्ट करें।
3. सक्रिय SIM कार्ड (SMS सुविधा के साथ) और एंटेना लगाना न भूलें।

स्क्रिप्ट चलाने के लिए:
- Termux में इस रिपोजिटरी को क्लोन करें।
- आवश्यक Python पैकेज (pyserial) इंस्टॉल करें: pip install pyserial
- फिर स्क्रिप्ट को रन करें: python3 renu.py
"""

import time
import serial

def send_sms_via_gsm(phone, message):
    """
    GSM मॉड्यूल के जरिए SMS भेजने का फंक्शन।
    सुनिश्चित करें कि आपके हार्डवेयर में नीचे दिए गए सभी कनेक्शन्स सही हैं:
      - GSM TX -> USB-to-TTL RX
      - GSM RX -> USB-to-TTL TX
      - पावर और ग्राउंड कनेक्शन ठीक से जुड़े हों
    """
    try:
        print("Initializing GSM module on /dev/ttyUSB0 with baudrate 115200...")
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        time.sleep(1)
        
        print("Sending AT command...")
        ser.write(b'AT\r')
        time.sleep(1)
        response = ser.read_all().decode(errors='ignore')
        print("AT Response:", response)
        
        print("Setting SMS text mode (AT+CMGF=1)...")
        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        response = ser.read_all().decode(errors='ignore')
        print("CMGF Response:", response)
        
        cmd = f'AT+CMGS="{phone}"\r'
        print("Sending SMS command:", cmd)
        ser.write(cmd.encode())
        time.sleep(1)
        
        print("Sending message content...")
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        
        print("Sending CTRL+Z to finalize SMS...")
        ser.write(bytes([26]))  # CTRL+Z to send SMS
        time.sleep(3)
        
        response = ser.read_all().decode(errors='ignore')
        print("Final Response:", response)
        ser.close()
        
        if "OK" in response:
            print("SMS successfully sent via GSM module.")
            return True
        else:
            print("Failed to send SMS via GSM module.")
            return False
    except Exception as e:
        print("Error in send_sms_via_gsm:", e)
        return False

def main():
    print("Offline SMS Sender Tool (renu.py)")
    print("----------------------------------")
    phone = input("Enter recipient phone number (with country code, e.g. +911234567890): ").strip()
    message = input("Enter the message to send: ").strip()
    
    print("\nSending SMS...")
    if send_sms_via_gsm(phone, message):
        print("SMS sent successfully.")
    else:
        print("SMS sending failed. Please check your GSM module setup and wiring.")

if __name__ == '__main__':
    main()
