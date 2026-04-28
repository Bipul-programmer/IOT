import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
from sklearn.metrics import accuracy_score

MODEL_PATH = "water_quality_model.joblib"
SCALER_PATH = "scaler.joblib"
IMPUTER_PATH = "imputer.joblib"
DATA_PATH = "water_potability.csv"

def train_model_best():
    if not os.path.exists(DATA_PATH):
        return None
    
    df = pd.read_csv(DATA_PATH)
    df['tds'] = df['Solids']
    df['turbidity'] = df['Turbidity']
    
    # 1. Imputation
    imputer = SimpleImputer(strategy='median')
    df[['ph', 'tds', 'turbidity']] = imputer.fit_transform(df[['ph', 'tds', 'turbidity']])
    
    # 2. Synthetic Temperature (20-30 C range)
    np.random.seed(42)
    df['temperature'] = np.random.uniform(20, 30, size=len(df))
    
    features = ['ph', 'temperature', 'turbidity', 'tds']
    X = df[features]
    y = df['Potability']
    
    # 3. Stratified Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 4. SMOTE for class balance
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    
    # 5. Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_res)
    X_test_scaled = scaler.transform(X_test)
    
    # 6. Random Forest with Optimized Parameters
    # We use a more restricted forest to prevent overfitting on the synthetic noise
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        class_weight='balanced_subsample'
    )
    model.fit(X_train_scaled, y_train_res)
    
    accuracy = model.score(X_test_scaled, y_test)
    print(f"Optimized Model Accuracy: {accuracy:.2f}")
    
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(imputer, IMPUTER_PATH)
    joblib.dump(features, "feature_names.joblib")
    
    return model

def predict_potability(input_data):
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    features = joblib.load("feature_names.joblib")
    input_df = pd.DataFrame([input_data])
    input_df = input_df[features]
    scaled_input = scaler.transform(input_df)
    prediction = model.predict(scaled_input)[0]
    probability = model.predict_proba(scaled_input)[0][1]
    return {
        "potable": int(prediction),
        "confidence": float(probability if prediction == 1 else 1 - probability),
        "contamination_level": float(1 - probability)
    }

if __name__ == "__main__":
    train_model_best()