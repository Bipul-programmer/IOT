import pandas as pd
import numpy as np
import joblib
import os
import threading
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE

MODEL_PATH = "water_quality_model.joblib"
SCALER_PATH = "scaler.joblib"
IMPUTER_PATH = "imputer.joblib"
FEATURES_PATH = "feature_names.joblib"

# Global cache for the model
_model_cache = {
    "model": None,
    "scaler": None,
    "imputer": None,
    "features": None
}
_cache_lock = threading.Lock()

def load_model_into_cache():
    """Loads the model and assets from disk into the global cache."""
    global _model_cache
    with _cache_lock:
        try:
            if os.path.exists(MODEL_PATH):
                _model_cache["model"] = joblib.load(MODEL_PATH)
                _model_cache["scaler"] = joblib.load(SCALER_PATH)
                _model_cache["imputer"] = joblib.load(IMPUTER_PATH)
                _model_cache["features"] = joblib.load(FEATURES_PATH)
                print("ML Model loaded into memory.")
                return True
        except Exception as e:
            print(f"Error loading model: {e}")
    return False

async def train_model_best():
    """Trains the model using data from MongoDB and saves it to disk."""
    from database import get_training_data
    data = await get_training_data()
    
    if not data:
        print("No training data found in MongoDB.")
        return None
    
    df = pd.DataFrame(data)
    
    # Standardize feature names
    mapping = {'Solids': 'tds', 'Turbidity': 'turbidity', 'Temperature': 'temperature'}
    for old_col, new_col in mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
            
    features = ['ph', 'temperature', 'turbidity', 'tds']
    
    # Imputation
    for f in features:
        if f not in df.columns:
            df[f] = np.nan
    imputer = SimpleImputer(strategy='median')
    df[features] = imputer.fit_transform(df[features])
    
    # Synthetic Temperature if missing or constant
    if df['temperature'].nunique() <= 1:
        df['temperature'] = np.random.uniform(20, 30, size=len(df))
    
    X = df[features]
    y = df['Potability']
    
    # Split & Balance
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    
    # Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_res)
    X_test_scaled = scaler.transform(X_test)
    
    # Train
    model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight='balanced')
    model.fit(X_train_scaled, y_train_res)
    
    print(f"Model trained. Accuracy: {model.score(X_test_scaled, y_test):.2f}")
    
    # Save to disk
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(imputer, IMPUTER_PATH)
    joblib.dump(features, FEATURES_PATH)
    
    # Refresh cache
    load_model_into_cache()
    return model

def get_contamination_reasons(data):
    """Analyzes features to identify specific reasons for contamination."""
    reasons = []
    
    # pH Analysis (Standard: 6.5 - 8.5)
    if data.get('ph') is not None:
        if data['ph'] < 6.5:
            reasons.append("Acidic pH: Possible chemical runoff or industrial discharge.")
        elif data['ph'] > 8.5:
            reasons.append("Alkaline pH: Possible mineral leaching or detergent contamination.")
            
    # TDS Analysis (Standard: < 500 ppm)
    if data.get('tds') is not None:
        if data['tds'] > 500:
            reasons.append("High TDS: Indicates high mineral content, industrial runoff, or sewage.")
            
    # Turbidity Analysis (Standard: < 5 NTU)
    if data.get('turbidity') is not None:
        if data['turbidity'] > 5:
            reasons.append("High Turbidity: Presence of suspended solids, sediment, or bacteria.")
            
    # Temperature Analysis (Ideal: < 30°C)
    if data.get('temperature') is not None:
        if data['temperature'] > 30:
            reasons.append("High Temperature: Increases bacterial growth risk and reduces oxygen levels.")
            
    return reasons if reasons else ["No significant anomalies detected in individual parameters."]

def predict_potability(input_data):
    """Performs inference and provides contamination analysis."""
    global _model_cache
    
    # Ensure cache is loaded
    if _model_cache["model"] is None:
        if not load_model_into_cache():
            # Fallback/Default if no model exists
            return {
                "potable": 0, 
                "confidence": 0.5, 
                "contamination_level": 0.5,
                "reasons": ["Model not loaded. Using default thresholds."]
            }

    try:
        input_df = pd.DataFrame([input_data])
        input_df = input_df[_model_cache["features"]]
        
        # Scale
        scaled_input = _model_cache["scaler"].transform(input_df)
        
        prediction = _model_cache["model"].predict(scaled_input)[0]
        probability = _model_cache["model"].predict_proba(scaled_input)[0][1]
        
        # Get specific reasons
        reasons = get_contamination_reasons(input_data)
        
        return {
            "potable": int(prediction),
            "confidence": float(probability if prediction == 1 else 1 - probability),
            "contamination_level": float(1 - probability),
            "reasons": reasons
        }
    except Exception as e:
        print(f"Inference error: {e}")
        return {
            "potable": 0, 
            "confidence": 0.0, 
            "contamination_level": 1.0,
            "reasons": [f"Error during analysis: {str(e)}"]
        }

if __name__ == "__main__":
    import asyncio
    asyncio.run(train_model_best())