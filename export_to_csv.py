import asyncio
import csv
import os
from database import sensor_data_collection

async def export_data():
    output_file = "exported_sensor_data.csv"
    print(f"Exporting data from MongoDB to {output_file}...")
    
    cursor = sensor_data_collection.find()
    count = 0
    
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['sensor_id', 'ph', 'temperature', 'turbidity', 'tds', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        async for doc in cursor:
            writer.writerow({
                'sensor_id': doc.get('sensor_id'),
                'ph': doc.get('ph'),
                'temperature': doc.get('temperature'),
                'turbidity': doc.get('turbidity'),
                'tds': doc.get('tds'),
                'timestamp': doc.get('timestamp')
            })
            count += 1
            
    print(f"Successfully exported {count} records.")

if __name__ == "__main__":
    asyncio.run(export_data())
