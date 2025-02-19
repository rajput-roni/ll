def send_sms_via_gsm(phone, message):
    try:
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=5)
        ser.write(b'AT\r')
        time.sleep(1)
        response = ser.read_all().decode()
        print("AT Response:", response)
        if "OK" not in response:
            return False

        ser.write(b'AT+CMGF=1\r')
        time.sleep(1)
        response = ser.read_all().decode()
        print("AT+CMGF=1 Response:", response)
        if "OK" not in response:
            return False

        cmd = f'AT+CMGS="{phone}"\r'
        ser.write(cmd.encode())
        time.sleep(1)
        ser.write(message.encode() + b"\r")
        time.sleep(1)
        ser.write(bytes([26]))  # Ctrl+Z to send the message
        time.sleep(3)
        response = ser.read_all().decode()
        ser.close()
        print("Send SMS Response:", response)
        if "OK" in response:
            print("SMS sent successfully")
            sys.stdout.flush()
            return True
        else:
            return False
    except Exception as e:
        print("Error in send_sms_via_gsm:", e)
        return False
