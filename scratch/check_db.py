import asyncio
from database import sensor_data_collection, predictions_collection

async def check():
    sensor_count = await sensor_data_collection.count_documents({})
    prediction_count = await predictions_collection.count_documents({})
    print(f"Sensor Readings: {sensor_count}")
    print(f"Predictions: {prediction_count}")

if __name__ == "__main__":
    asyncio.run(check())
