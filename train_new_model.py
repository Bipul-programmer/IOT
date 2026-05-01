import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

def train_model():
    print("Loading data...")
    if not os.path.exists("new_sensorData.csv"):
        print("Error: new_sensorData.csv not found.")
        return

    df = pd.read_csv("new_sensorData.csv")
    
    X = df.drop('Potability', axis=1)
    y = df['Potability']
    
    # Preprocessing
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)
    
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    
    print("Comparing models...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    
    rf.fit(X_train, y_train)
    gb.fit(X_train, y_train)
    
    rf_acc = accuracy_score(y_test, rf.predict(X_test))
    gb_acc = accuracy_score(y_test, gb.predict(X_test))
    
    print(f"Random Forest Accuracy: {rf_acc:.4f}")
    print(f"Gradient Boosting Accuracy: {gb_acc:.4f}")
    
    # Choose best
    if gb_acc >= rf_acc:
        best_model = gb
        print("Selected Gradient Boosting.")
    else:
        best_model = rf
        print("Selected Random Forest.")
        
    # Save assets
    joblib.dump(best_model, "water_quality_model.joblib")
    joblib.dump(scaler, "scaler.joblib")
    joblib.dump(imputer, "imputer.joblib")
    joblib.dump(list(X.columns), "feature_names.joblib")
    
    print("Model and assets saved successfully.")

if __name__ == "__main__":
    train_model()
