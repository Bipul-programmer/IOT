from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from database import save_sensor_data, save_prediction, get_all_history
from ml_model import predict_potability, train_model_refined
import datetime

app = FastAPI(title="Water Quality Monitoring System")

class SensorReading(BaseModel):
    sensor_id: str
    ph: float
    temperature: float
    turbidity: float
    tds: float
    location: Optional[str] = "Main Tank"

@app.get("/")
async def root():
    return {"message": "Water Quality Monitoring API is running"}

@app.post("/ingest")
async def ingest_data(reading: SensorReading):
    prediction_result = predict_potability(reading.model_dump())
    data_id = await save_sensor_data(reading.model_dump())
    
    quality_label = "Safe" if prediction_result["potable"] == 1 else "Unsafe"
    
    prediction_record = {
        "sensor_id": reading.sensor_id,
        "reading_id": data_id,
        "sensor_data": reading.model_dump(),
        "quality": quality_label,
        "potability_score": prediction_result["confidence"],
        "contamination_level": prediction_result["contamination_level"],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    await save_prediction(prediction_record)
    
    return {
        "status": "success",
        "data_id": data_id,
        "prediction": quality_label,
        "contamination_level": prediction_result["contamination_level"]
    }

@app.get("/history")
async def get_history(limit: int = 20):
    history = await get_all_history(limit)
    return {"history": history}

@app.post("/retrain")
async def retrain():
    train_model_refined()
    return {"status": "Model retrained successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
