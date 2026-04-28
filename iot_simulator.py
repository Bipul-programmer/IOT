import requests
import time
import random

API_URL = "http://localhost:8000/ingest"

def simulate_iot_device(sensor_id="IOT_SENSOR_001"):
    print(f"Starting IoT Simulator for {sensor_id}...")
    
    while True:
        # Simulate only the 4 required features
        ph = round(random.uniform(6.5, 8.5), 2)
        temperature = round(random.uniform(18.0, 32.0), 1)
        turbidity = round(random.uniform(0.0, 5.0), 2)
        tds = round(random.uniform(200, 800), 0)
        
        payload = {
            "sensor_id": sensor_id,
            "ph": ph,
            "temperature": temperature,
            "turbidity": turbidity,
            "tds": tds,
            "location": "Primary Outlet"
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                print(f"[{time.strftime('%H:%M:%S')}] Data Sent! Prediction: {result['prediction']} | Contamination: {result['contamination_level']:.2f}")
            else:
                print(f"Failed to send data: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error connecting to backend: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    simulate_iot_device()
