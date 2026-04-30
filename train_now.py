import asyncio
from ml_model import train_model_best, load_model_into_cache
import os

async def main():
    print("--- Water Quality Model Trainer ---")
    
    # 1. Check if collected data exists
    if os.path.exists("collected_data.csv"):
        print("Found 'collected_data.csv'.")
    else:
        print("Warning: 'collected_data.csv' not found. Training will use base data from MongoDB.")
    
    print("Starting training process...")
    model = await train_model_best()
    
    if model:
        print("Training completed successfully!")
        print("Model saved to: water_quality_model.joblib")
        
        # Reload cache to use the new model immediately
        load_model_into_cache()
        print("Model cache updated.")
    else:
        print("Training failed. Please check if you have enough data.")

if __name__ == "__main__":
    asyncio.run(main())
