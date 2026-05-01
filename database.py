import os
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "water_quality_monitor"

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# --- MongoDB Schemas ---

class SensorReadingSchema(BaseModel):
    sensor_id: str
    village: Optional[str] = "Global"
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    ph: float
    temperature: float
    turbidity: float
    tds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PredictionSchema(BaseModel):
    sensor_id: str
    reading_id: str
    sensor_data: dict
    quality: str
    potability_score: float
    contamination_level: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- Collections ---
sensor_data_collection = db["sensor_readings"]
predictions_collection = db["predictions"]
training_data_collection = db["training_data"]

# --- Operations ---

async def save_sensor_data(data: dict):
    result = await sensor_data_collection.insert_one(data)
    return str(result.inserted_id)

async def save_prediction(prediction_data: dict):
    result = await predictions_collection.insert_one(prediction_data)
    return str(result.inserted_id)

async def get_all_history(limit: int = 100):
    cursor = predictions_collection.find().sort("timestamp", -1).limit(limit)
    history = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        history.append(document)
    return history

async def get_all_sensors():
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$sensor_id",
            "latest_reading": {"$first": "$$ROOT"}
        }}
    ]
    cursor = sensor_data_collection.aggregate(pipeline)
    sensors = []
    async for item in cursor:
        doc = item["latest_reading"]
        sensors.append({
            "id": doc["sensor_id"],
            "village": doc.get("village", "Global"),
            "readings": {
                "ph": doc["ph"],
                "tds": doc["tds"],
                "turbidity": doc["turbidity"],
                "temperature": doc["temperature"]
            }
        })
    return sensors
