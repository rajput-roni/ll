import serial
import time

# Set the correct serial port and baud rate for your GSM module
gsm = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

def check_gsm_connection():
    try:
        # Send basic AT command to check connection
        gsm.write(b'AT\r')
        time.sleep(1)
        response = gsm.read_all().decode()
        print("AT Response:", response)
        
        # Check if the response contains 'OK'
        if "OK" in response:
            print("[✅] GSM module is connected and working!")
        else:
            print("[❌] GSM module is not responding correctly.")
    except Exception as e:
        print("Error:", e)

# Check GSM connection
check_gsm_connection()
