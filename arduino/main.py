import serial
import time
import requests

# Change this to your Arduino COM port
arduino = serial.Serial('COM5', 9600, timeout=1)
time.sleep(5)  # wait for Arduino to reset
print("Serial Open")

SERVER_URL = 'http://10.48.105.115:8080'

# def send_to_arduino (val):
#     try:
#         arduino.write(val.encode())
#         print("Sent: {val}")
#     except Exception as e:
#         print(":( {val} not sent")

# arduino.write(bytes("true\n", 'utf-8'))

while True:
    try:
        r = requests.get(SERVER_URL, timeout=5)
        if "true" in r.text or "True" in r.text:
            print("sending true to arduino")
            arduino.write(b"true\n")
        else:
            print("sending false to arduino")
            arduino.write(b"false\n")
        time.sleep(1)
    except requests.RequestException:
        arduino.write(b"invalid\n")

# while True:
#     try:
#         r = requests.get(SERVER_URL, timeout=5)
#         print(r.text)
#         if "true" in r.text:
#             print("is true")
#             arduino.write(bytes("true\n", 'utf-8'))
#         else:
#             print("is false")
#             arduino.write(bytes("false\n", 'utf-8'))
#         print(arduino.readline())
#     except requests.RequestException:
#         arduino.write(b"false\n")

#     time.sleep(5)  # check every 5 seconds