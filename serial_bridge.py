import serial
import serial.tools.list_ports
import requests
import time
import os

# --- CONFIGURATION ---
API_URL = "http://localhost:8000/ingest"
BAUD_RATE = 115200

def find_esp32_port():
    """Attempts to find the ESP32 serial port on macOS."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Common ESP32/Arduino serial port identifiers on Mac
        if "usbserial" in port.device.lower() or "usbmodem" in port.device.lower():
            return port.device
    return None

def is_valid(data):
    """Basic validation for sensor readings."""
    try:
        return (
            0 <= data["ph"] <= 14 and
            0 <= data["tds"] <= 2000 and
            0 <= data["turbidity"] <= 1000 and
            -10 <= data["temperature"] <= 80
        )
    except:
        return False

def parse_line(line):
    """Parses raw serial strings like 'pH=6.2,TDS=100,Turb=5.1,Temp=34.5'"""
    key_map = {
        "ph": ["ph"],
        "temperature": ["temp", "temperature"],
        "turbidity": ["turb", "turbidity"],
        "tds": ["tds"]
    }

    data_map = {}
    for part in line.split(','):
        if '=' in part:
            parts = part.split('=', 1)
            if len(parts) == 2:
                k, v = parts
                data_map[k.strip().lower()] = v.strip()

    parsed = {}
    for std_key, aliases in key_map.items():
        for alias in aliases:
            if alias in data_map:
                try:
                    parsed[std_key] = float(data_map[alias])
                except:
                    return None
                break

    if len(parsed) == 4:
        return {
            "sensor_id": "ESP32_PHYSICAL",
            **parsed,
            "village": "Real-time Site",
            "location": "Physical Sensor"
        }
    return None

def main():
    port = find_esp32_port()
    if not port:
        print("❌ Error: ESP32 not found. Please ensure it's connected via USB.")
        return

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {port} at {BAUD_RATE} baud.")
    except Exception as e:
        print(f"❌ Failed to connect to serial port: {e}")
        return

    print("🚀 Listening for sensor data... (Press Ctrl+C to stop)")
    
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                
                print(f"RAW: {line}")
                payload = parse_line(line)

                if not payload:
                    print(f"⚠️ Parse failed for line: {line}")
                    continue

                if not is_valid(payload):
                    print(f"⚠️ Invalid data filtered: {payload}")
                    continue

                # Send to Central API (Backend handles CSV logging & MongoDB)
                try:
                    response = requests.post(API_URL, json=payload, timeout=5)
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ Sent! Result: {result.get('prediction')} | Contamination: {result.get('contamination_level')}%")
                    else:
                        print(f"❌ Backend error: {response.status_code}")
                except Exception as e:
                    print(f"❌ API connection error: {e}")

    except KeyboardInterrupt:
        print("\n👋 Serial bridge stopped.")

if __name__ == "__main__":
    main()
