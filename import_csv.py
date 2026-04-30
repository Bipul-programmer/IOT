import asyncio
import os
from database import import_csv_to_db

async def main():
    csv_path = "water_potability_clean.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
    
    print(f"Importing {csv_path} into MongoDB...")
    count = await import_csv_to_db(csv_path)
    print(f"Successfully imported {count} records into 'training_data' collection.")

if __name__ == "__main__":
    asyncio.run(main())
