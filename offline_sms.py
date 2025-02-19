import serial
import time

# GSM Module का Serial Port और Baudrate सेट करें
gsm = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

def send_sms(number, message):
    gsm.write(b'AT+CMGF=1\r')  # Text Mode Enable करें
    time.sleep(1)
    gsm.write(f'AT+CMGS="{number}"\r'.encode())  # Recipient Number Set करें
    time.sleep(1)
    gsm.write(message.encode() + b"\x1A")  # Message Send करें
    time.sleep(3)
    print("[✅] SMS Sent Successfully!")

# Example Call
send_sms("+919695003501", "Hello! This is an offline SMS system!")
