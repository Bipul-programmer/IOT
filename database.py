import os
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "water_quality_db"

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Collections
sensor_data_collection = db["sensor_data"]
predictions_collection = db["predictions"]

async def save_sensor_data(data: dict):
    data["timestamp"] = datetime.utcnow()
    result = await sensor_data_collection.insert_one(data)
    return str(result.inserted_id)

async def save_prediction(prediction: dict):
    prediction["timestamp"] = datetime.utcnow()
    result = await predictions_collection.insert_one(prediction)
    return str(result.inserted_id)

async def get_latest_sensor_data(sensor_id: str):
    return await sensor_data_collection.find_one({"sensor_id": sensor_id}, sort=[("timestamp", -1)])

async def get_all_history(limit: int = 100):
    cursor = predictions_collection.find().sort("timestamp", -1).limit(limit)
    history = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        history.append(document)
    return history
