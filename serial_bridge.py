import serial
import serial.tools.list_ports
import requests
import json
import time
import csv
import os

# --- CONFIGURATION ---
API_URL = "http://localhost:8000/ingest"
BAUD_RATE = 115200
CSV_FILENAME = "sensor_log.csv"

def find_esp32_port():
    """
    Attempts to find the ESP32 serial port on macOS.
    """
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports detected at all.")
        return None
        
    print(f"Scanning {len(ports)} serial ports...")
    for port in ports:
        print(f" - Found port: {port.device} ({port.description})")
        # Common ESP32/Arduino serial port identifiers on Mac
        if "usbserial" in port.device.lower() or "usbmodem" in port.device.lower():
            print(f">>> Identified ESP32 on port: {port.device}")
            return port.device
    return None

def main():
    port = find_esp32_port()
    if not port:
        print("Error: ESP32 not found. Please ensure it's connected via USB.")
        return

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"Connected to {port} at {BAUD_RATE} baud.")
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        return

    print("Listening for LoRa data... (Press Ctrl+C to stop)")
    
    while True:
        if ser.in_waiting > 0:
            try:
                # Read line from serial
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                
                print(f"Received: {line}")
                
                # Attempt to parse data
                # We assume the data is either JSON or Comma Separated: sensor_id,ph,temp,turb,tds
                payload = {}
                
                if line.startswith('{') and line.endswith('}'):
                    # It's JSON
                    payload = json.loads(line)
                elif ',' in line:
                    # It's CSV: IOT_001,6.5,24.5,610,95
                    parts = line.split(',')
                    if len(parts) >= 5:
                        payload = {
                            "sensor_id": parts[0],
                            "ph": float(parts[1]),
                            "temperature": float(parts[2]),
                            "turbidity": float(parts[3]),
                            "tds": float(parts[4]),
                            "location": "LoRa Node"
                        }
                
                if payload:
                    # 1. Save to local CSV
                    file_exists = os.path.isfile(CSV_FILENAME)
                    with open(CSV_FILENAME, mode='a', newline='') as f:
                        fieldnames = ["timestamp", "sensor_id", "ph", "temperature", "turbidity", "tds", "location"]
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        if not file_exists:
                            writer.writeheader()
                        
                        row = payload.copy()
                        row["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                        # Ensure all fields exist
                        for field in fieldnames:
                            if field not in row:
                                row[field] = ""
                        writer.writerow({k: row[k] for k in fieldnames})
                    
                    print(f"Data saved to {CSV_FILENAME}")

                    # 2. Send to MongoDB backend
                    try:
                        response = requests.post(API_URL, json=payload)
                        if response.status_code == 200:
                            print(f"Successfully sent to MongoDB! Prediction: {response.json().get('prediction')}")
                        else:
                            print(f"Backend error: {response.status_code} - {response.text}")
                    except Exception as e:
                        print(f"Could not connect to backend: {e}")
                
            except json.JSONDecodeError:
                print("Error: Received invalid JSON.")
            except ValueError as e:
                print(f"Error parsing values: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()
