import asyncio
import pandas as pd
from database import sensor_data_collection

async def import_csv(file_path):
    print(f"Importing data from {file_path} to MongoDB...")
    df = pd.read_csv(file_path)
    records = df.to_dict('records')
    
    if records:
        await sensor_data_collection.insert_many(records)
        print(f"Successfully imported {len(records)} records.")
    else:
        print("No records found in CSV.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(import_csv(sys.argv[1]))
    else:
        print("Usage: python import_csv.py <path_to_csv>")
