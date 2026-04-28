from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional, Literal
import sqlite3, os, joblib, random
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from uuid import uuid4
from fastapi import WebSocket, WebSocketDisconnect

# -------------------- CONFIG --------------------
SECRET_KEY = "supersecretkey"  # change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# -------------------- FASTAPI APP --------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- WEBSOCKET MANAGER --------------------
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

# -------------------- DATABASE --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "water_safety.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_db_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

def init_database():
    conn, cur = get_db_cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT CHECK(role IN ('admin','user')),
        village TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_data (
        id TEXT PRIMARY KEY,
        village TEXT,
        lat REAL,
        lng REAL,
        temperature REAL,
        ph REAL,
        turbidity REAL,
        tds REAL,
        status TEXT,
        last_updated TEXT,
        name TEXT,
        type TEXT,
        manufacturer TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id TEXT,
        village TEXT,
        temperature REAL,
        ph REAL,
        turbidity REAL,
        tds REAL,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS health_reports (
        id TEXT PRIMARY KEY,
        village TEXT,
        symptoms TEXT,
        created_at TEXT,
        phone TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        sensor_id TEXT,
        message TEXT,
        level TEXT,
        timestamp TEXT,
        acknowledged INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

init_database()

# -------------------- MODELS --------------------
try:
    model = joblib.load("model.pkl")
except:
    model = None

ML_MODELS_AVAILABLE = False
try:
    from water_safety_model import predict_water_safety, predict_disease
    ML_MODELS_AVAILABLE = True
except:
    pass

# -------------------- SCHEMAS --------------------
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal['admin', 'user']
    village: Optional[str] = None

class SensorReading(BaseModel):
    id: str
    village: str
    lat: float
    lng: float
    temperature: float
    ph: float
    turbidity: float
    tds: float
    name: Optional[str] = None
    type: Optional[str] = None
    manufacturer: Optional[str] = None

class HealthReport(BaseModel):
    id: str
    village: str
    symptoms: List[str]
    phone: Optional[str] = None

class PublicHealthReport(BaseModel):
    id: Optional[str] = None
    village: str
    symptoms: List[str]
    phone: str

class PredictRequest(BaseModel):
    sensor_id: str
    village: str
    temperature: float
    ph: float
    turbidity: float
    tds: float

# -------------------- AUTH HELPERS --------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(username: str):
    conn, cur = get_db_cursor()
    cur.execute("SELECT username, password, role, village FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "password": row[1], "role": row[2], "village": row[3]}
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user["password"]):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

def require_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user

# -------------------- ROUTES --------------------
@app.post("/signup")
def signup(user: UserCreate):
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    conn, cur = get_db_cursor()
    cur.execute("INSERT INTO users (username, password, role, village) VALUES (?, ?, ?, ?)",
                (user.username, hashed_pw, user.role, user.village))
    conn.commit()
    conn.close()
    return {"msg": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"], "village": user.get("village")})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/public/sensor_data")
async def add_sensor_data_public(sensor: SensorReading):
    now = datetime.utcnow().isoformat()
    conn, cur = get_db_cursor()
    cur.execute("""
        INSERT OR REPLACE INTO sensor_data
        (id, village, lat, lng, temperature, ph, turbidity, tds, status, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sensor.id, sensor.village, sensor.lat, sensor.lng, sensor.temperature, sensor.ph, sensor.turbidity, sensor.tds, "online", now))
    cur.execute("""
        INSERT INTO sensor_history (sensor_id, village, temperature, ph, turbidity, tds, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sensor.id, sensor.village, sensor.temperature, sensor.ph, sensor.turbidity, sensor.tds, now))
    conn.commit()
    conn.close()
    await manager.broadcast({"type": "sensor_update", "sensor": sensor.dict()})
    return {"status": "ok"}

@app.get("/sensors")
def get_sensors():
    conn, cur = get_db_cursor()
    cur.execute("SELECT * FROM sensor_data")
    rows = cur.fetchall()
    conn.close()
    sensors = []
    for r in rows:
        sensors.append({
            "id": r[0], "village": r[1], "location": {"lat": r[2], "lng": r[3]},
            "status": r[8], "last_updated": r[9],
            "readings": {"temperature": r[4], "ph": r[5], "turbidity": r[6], "tds": r[7]}
        })
    return {"sensors": sensors}

@app.post("/public/predict")
def public_predict(data: PredictRequest):
    if ML_MODELS_AVAILABLE:
        safety_result = predict_water_safety(data.temperature, data.ph, data.turbidity, data.tds)
        disease_result = predict_disease(data.temperature, data.ph, data.turbidity, data.tds)
        return {
            "sensor_id": data.sensor_id, "village": data.village,
            "water_safety": safety_result, "disease_prediction": disease_result
        }
    else:
        unsafe = data.ph < 6.5 or data.ph > 8.5 or data.turbidity > 10 or data.tds > 500
        result = "Unsafe" if unsafe else "Safe"
        return {"sensor_id": data.sensor_id, "village": data.village, "result": result, "confidence": 0.85}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
