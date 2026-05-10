import serial
import requests
import json
import time

# --- CONFIGURATION ---
# This must match your Arduino's serial port.
# On Windows, it's 'COM3', 'COM4', etc.
# On macOS/Linux, it's '/dev/tty.usbmodem...' or '/dev/ttyUSB0'
SERIAL_PORT = 'COM7'  # !! IMPORTANT: CHANGE THIS !!
BAUD_RATE = 9600
FLASK_API_URL = 'http://127.0.0.1:5000/api/authorize'
# --- END CONFIGURATION ---

def main():
    print("Starting Kiosk Bridge...")
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to Arduino on {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"Fatal Error: Could not connect to {SERIAL_PORT}.")
        print(f"Error details: {e}")
        print("Please check your SERIAL_PORT variable and device connection.")
        return

    while True:
        try:
            # 1. Read a line from the Arduino
            data = arduino.readline().decode('utf-8').strip()

            if data and "Ready" not in data:
                # We received an RFID UID
                print(f"RFID Scanned: {data}")
                
                # 2. Send the UID to the Flask API
                try:
                    response = requests.post(FLASK_API_URL, json={'rfid_uid': data})
                    api_data = response.json()

                    if response.status_code == 200:
                        # Success: Send "SUCCESS:Name" to Arduino
                        user_name = api_data.get('user_name', 'User')
                        print(f"API Response: Success, User: {user_name}")
                        arduino.write(f"SUCCESS:{user_name}\n".encode())
                    else:
                        # Error (404, 403, etc.): Send "ERROR:Message" to Arduino
                        message = api_data.get('message', 'Error')
                        print(f"API Response: Error, {message}")
                        arduino.write(f"ERROR:{message}\n".encode())
                
                except requests.exceptions.RequestException as e:
                    print(f"API Error: Could not connect to Flask app. {e}")
                    arduino.write(b"ERROR:No Connection\n")

        except KeyboardInterrupt:
            print("Stopping bridge...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(1)

    arduino.close()

if __name__ == "__main__":
    main()