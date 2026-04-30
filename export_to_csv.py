import asyncio
import csv
import os
from database import sensor_data_collection

async def export_sensors_to_csv(filename="sensor_export.csv"):
    print(f"Exporting data from MongoDB to {filename}...")
    
    # Fetch all records
    cursor = sensor_data_collection.find().sort("timestamp", 1)
    
    count = 0
    with open(filename, mode='w', newline='') as f:
        fieldnames = ["timestamp", "sensor_id", "village", "ph", "temperature", "turbidity", "tds", "potability", "lat", "lng", "location"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        async for doc in cursor:
            # Note: We might need to fetch the prediction to get potability if it's not in sensor_readings
            # For simplicity, we'll try to get it from the doc if it exists
            row = {
                "timestamp": doc["timestamp"].isoformat() if "timestamp" in doc else "",
                "sensor_id": doc.get("sensor_id", ""),
                "village": doc.get("village", ""),
                "ph": doc.get("ph", ""),
                "temperature": doc.get("temperature", ""),
                "turbidity": doc.get("turbidity", ""),
                "tds": doc.get("tds", ""),
                "potability": doc.get("potability", ""),
                "lat": doc.get("lat", ""),
                "lng": doc.get("lng", ""),
                "location": doc.get("location", "")
            }
            writer.writerow(row)
            count += 1
            
    print(f"Successfully exported {count} records to {filename}")

if __name__ == "__main__":
    asyncio.run(export_sensors_to_csv())
