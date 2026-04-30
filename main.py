from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import datetime
from fastapi import WebSocket, WebSocketDisconnect
from database import save_sensor_data, save_prediction, get_all_history, get_all_sensors
from ml_model import predict_potability, train_model_best, load_model_into_cache
import csv
import os

app = FastAPI(title="Water Quality Monitoring System")

# Global counter for periodic retraining
ingestion_counter = 0
RETRAIN_THRESHOLD = 50 # Retrain every 50 new readings
COLLECTED_DATA_CSV = "collected_data.csv"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Initializing Water Quality System...")
    # 1. Try to load existing model
    success = load_model_into_cache()
    if not success:
        print("No existing model found. Training initial model...")
        await train_model_best()

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        stale = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for s in stale:
            self.disconnect(s)

manager = ConnectionManager()

class SensorReading(BaseModel):
    sensor_id: str
    village: Optional[str] = "Global"
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    ph: float
    temperature: float
    turbidity: float
    tds: float
    location: Optional[str] = "Main Tank"

class PredictRequest(BaseModel):
    sensor_id: str
    village: str
    temperature: float
    ph: float
    turbidity: float
    tds: float

@app.get("/")
async def root():
    return {"message": "Water Quality Monitoring API is running"}

@app.post("/ingest")
async def ingest_data(reading: SensorReading, background_tasks: BackgroundTasks):
    global ingestion_counter
    
    # Perform prediction
    prediction_result = predict_potability(reading.model_dump())
    
    # Save raw data to MongoDB
    data_id = await save_sensor_data(reading.model_dump())
    
    quality_label = "Safe" if prediction_result["potable"] == 1 else "Unsafe"
    
    # Prepare prediction record
    prediction_record = {
        "sensor_id": reading.sensor_id,
        "reading_id": data_id,
        "sensor_data": reading.model_dump(),
        "quality": quality_label,
        "potability_score": prediction_result["confidence"],
        "contamination_level": prediction_result["contamination_level"],
        "reasons": prediction_result.get("reasons", []),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    # Save prediction to MongoDB
    await save_prediction(prediction_record)
    
    # --- CSV Logging ---
    file_exists = os.path.isfile(COLLECTED_DATA_CSV)
    with open(COLLECTED_DATA_CSV, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['ph', 'temperature', 'turbidity', 'tds', 'Potability', 'timestamp'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'ph': reading.ph,
            'temperature': reading.temperature,
            'turbidity': reading.turbidity,
            'tds': reading.tds,
            'Potability': prediction_result["potable"],
            'timestamp': prediction_record["timestamp"]
        })
    
    # Broadcast to WebSockets for real-time dashboard updates
    await manager.broadcast({
        "type": "sensor_update",
        "sensor": {
            "id": reading.sensor_id,
            "village": reading.village,
            "ph": reading.ph,
            "tds": reading.tds,
            "turbidity": reading.turbidity,
            "temperature": reading.temperature,
            "quality": quality_label,
            "reasons": prediction_result.get("reasons", [])
        }
    })
    
    # Periodic retraining logic
    ingestion_counter += 1
    if ingestion_counter >= RETRAIN_THRESHOLD:
        print(f"Threshold reached ({ingestion_counter}). Triggering model retraining...")
        background_tasks.add_task(train_model_best)
        ingestion_counter = 0
    
    return {
        "status": "success",
        "data_id": data_id,
        "prediction": quality_label,
        "reasons": prediction_result.get("reasons", []),
        "contamination_level": prediction_result["contamination_level"]
    }

# Compatibility alias for the vanilla JS frontend
@app.post("/public/sensor_data")
async def public_ingest(reading: SensorReading, background_tasks: BackgroundTasks):
    return await ingest_data(reading, background_tasks)

@app.get("/sensors")
async def list_sensors():
    sensors = await get_all_sensors()
    return {"sensors": sensors}

@app.get("/history")
async def get_history(limit: int = 20):
    history = await get_all_history(limit)
    return {"history": history}

@app.post("/public/predict")
async def public_predict(data: PredictRequest):
    features = {
        "ph": data.ph,
        "temperature": data.temperature,
        "turbidity": data.turbidity,
        "tds": data.tds
    }
    prediction = predict_potability(features)
    quality = "Safe" if prediction["potable"] == 1 else "Unsafe"
    return {
        "sensor_id": data.sensor_id,
        "village": data.village,
        "result": quality,
        "confidence": prediction["confidence"],
        "contamination_level": prediction["contamination_level"],
        "reasons": prediction.get("reasons", [])
    }

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.post("/retrain")
async def retrain():
    await train_model_best()
    return {"status": "Model retrained successfully"}

@app.get("/download_csv")
async def download_csv():
    if os.path.exists(COLLECTED_DATA_CSV):
        return FileResponse(
            path=COLLECTED_DATA_CSV, 
            filename=f"water_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            media_type="text/csv"
        )
    raise HTTPException(status_code=404, detail="CSV file not found. No data ingested yet.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
