from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import datetime
from database import save_sensor_data, get_all_history
import uvicorn

app = FastAPI()

class SensorReading(BaseModel):
    sensor_id: str
    ph: float
    temperature: float
    turbidity: float
    tds: float

@app.get("/")
async def root():
    return {"status": "Old Backend is Online"}

@app.post("/ingest")
async def ingest(reading: SensorReading):
    data = reading.dict()
    data["timestamp"] = datetime.datetime.now()
    await save_sensor_data(data)
    return {"status": "received"}

@app.get("/history")
async def history():
    return await get_all_history()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) # Runs on different port to avoid conflict
