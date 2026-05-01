import asyncio
from ml_model import train_model_best

async def main():
    print("Starting manual model retraining...")
    result = await train_model_best()
    if result:
        print("Model retrained and saved successfully.")
    else:
        print("Retraining failed or no data available.")

if __name__ == "__main__":
    asyncio.run(main())
