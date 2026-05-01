import pandas as pd
import numpy as np
import os

def generate_water_data(num_samples=5000):
    np.random.seed(42)
    
    # Feature ranges
    ph = np.random.uniform(4.0, 11.0, num_samples)
    temperature = np.random.uniform(10.0, 40.0, num_samples)
    turbidity = np.random.uniform(0.0, 15.0, num_samples)
    tds = np.random.uniform(50.0, 1200.0, num_samples)
    
    # Simple logic for potability (Potability = 1 is Safe)
    # Safe water generally has:
    # pH between 6.5 and 8.5
    # Turbidity < 5
    # TDS < 500
    
    potability = []
    for i in range(num_samples):
        is_potable = 1
        if not (6.5 <= ph[i] <= 8.5):
            is_potable = 0
        if turbidity[i] > 5.0:
            is_potable = 0
        if tds[i] > 500.0:
            is_potable = 0
            
        # Add some noise/randomness
        if np.random.random() < 0.1:
            is_potable = 1 - is_potable
            
        potability.append(is_potable)
        
    df = pd.DataFrame({
        'ph': ph,
        'temperature': temperature,
        'turbidity': turbidity,
        'tds': tds,
        'Potability': potability
    })
    
    output_file = "new_sensorData.csv"
    df.to_csv(output_file, index=False)
    print(f"Generated {num_samples} samples and saved to {output_file}")

if __name__ == "__main__":
    generate_water_data()
