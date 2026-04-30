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

# --- MongoDB Schemas (using Pydantic) ---

class SensorReadingSchema(BaseModel):
    sensor_id: str = Field(..., example="IOT_001")
    village: Optional[str] = "Global"
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    ph: float = Field(..., ge=0, le=14)
    temperature: float = Field(..., ge=-20, le=100)
    turbidity: float = Field(..., ge=0)
    tds: float = Field(..., ge=0)
    location: Optional[str] = "Main Tank"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PredictionSchema(BaseModel):
    sensor_id: str
    reading_id: str
    sensor_data: dict
    quality: str  # "Safe" or "Unsafe"
    potability_score: float
    contamination_level: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Collections ---
sensor_data_collection = db["sensor_readings"]
predictions_collection = db["predictions"]
training_data_collection = db["training_data"]

# --- Database Operations ---

async def save_sensor_data(data: dict):
    """
    Validates and saves raw sensor data to MongoDB.
    """
    reading = SensorReadingSchema(**data)
    result = await sensor_data_collection.insert_one(reading.model_dump())
    return str(result.inserted_id)

async def save_prediction(prediction_data: dict):
    """
    Saves the ML prediction result to MongoDB.
    """
    prediction = PredictionSchema(**prediction_data)
    result = await predictions_collection.insert_one(prediction.model_dump())
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

async def get_all_sensors():
    """
    Returns the latest reading for each unique sensor_id.
    """
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
            "location": {"lat": doc.get("lat", 0), "lng": doc.get("lng", 0)},
            "status": "online",
            "last_updated": doc["timestamp"].isoformat(),
            "readings": {
                "ph": doc["ph"],
                "tds": doc["tds"],
                "turbidity": doc["turbidity"],
                "temperature": doc["temperature"]
            }
        })
    return sensors

async def import_csv_to_db(csv_path: str):
    """
    Imports CSV data into the training_data collection.
    """
    import pandas as pd
    df = pd.read_csv(csv_path)
    # Ensure columns match what's expected or convert them
    # Based on water_potability_clean.csv: ph,Solids,Turbidity,Potability,Temperature
    data = df.to_dict(orient='records')
    if data:
        await training_data_collection.delete_many({}) # Clear old data if re-importing
        await training_data_collection.insert_many(data)
    return len(data)

async def get_training_data():
    """
    Fetches all training data, combining base CSV data, 
    live prediction data from MongoDB, and the new collected_data.csv.
    """
    data = []
    
    # 1. Base CSV Data from MongoDB (training_data collection)
    cursor_base = training_data_collection.find()
    async for document in cursor_base:
        document.pop("_id", None)
        # Standardize column names if necessary
        row = {
            "ph": document.get("ph"),
            "temperature": document.get("Temperature") or document.get("temperature"),
            "turbidity": document.get("Turbidity") or document.get("turbidity"),
            "tds": document.get("Solids") or document.get("tds"),
            "Potability": document.get("Potability")
        }
        if all(v is not None for v in row.values()):
            data.append(row)
    
    # 2. Live Data (from predictions in MongoDB)
    cursor_live = predictions_collection.find()
    async for document in cursor_live:
        p_data = document.get("sensor_data", {})
        row = {
            "ph": p_data.get("ph"),
            "temperature": p_data.get("temperature"),
            "turbidity": p_data.get("turbidity"),
            "tds": p_data.get("tds"),
            "Potability": 1 if document.get("quality") == "Safe" else 0
        }
        if all(v is not None for v in row.values()):
            data.append(row)
            
    # 3. New Collected Data from CSV
    csv_file = "collected_data.csv"
    if os.path.exists(csv_file):
        import pandas as pd
        try:
            df_collected = pd.read_csv(csv_file)
            # Filter for needed columns and convert to list of dicts
            needed = ["ph", "temperature", "turbidity", "tds", "Potability"]
            if all(col in df_collected.columns for col in needed):
                collected_list = df_collected[needed].to_dict(orient='records')
                data.extend(collected_list)
        except Exception as e:
            print(f"Error reading collected_data.csv: {e}")
            
    return data

