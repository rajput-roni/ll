import serial
import time

# GSM Module ka Serial Port aur Baud Rate
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200  # Yeh aapke module ke liye sahi hai

# Serial Connection Setup
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
ser.flush()

def send_sms(number, message):
    ser.write(b'AT+CMGF=1\r')  # SMS text mode enable karne ka command
    time.sleep(1)
    ser.write(f'AT+CMGS="{number}"\r'.encode())  # Number ko SMS bhejne ka command
    time.sleep(1)
    ser.write(f'{message}\x1A'.encode())  # Message aur Ctrl+Z (\x1A) to send
    time.sleep(3)
    print(f"SMS Sent to {number}")

# Example Usage
send_sms('919695003501', 'Message Body Here')
