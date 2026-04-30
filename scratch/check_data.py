import asyncio
from database import training_data_collection, predictions_collection

async def check():
    training_cursor = training_data_collection.find()
    base_labels = [doc.get("Potability") async for doc in training_cursor]
    
    predictions_cursor = predictions_collection.find()
    live_labels = []
    async for doc in predictions_cursor:
        live_labels.append(1 if doc.get("quality") == "Safe" else 0)
    
    print(f"Base Data (CSV): {len(base_labels)} samples, Distribution: { {l: base_labels.count(l) for l in set(base_labels)} }")
    print(f"Live Data (Predictions): {len(live_labels)} samples, Distribution: { {l: live_labels.count(l) for l in set(live_labels)} }")

if __name__ == "__main__":
    asyncio.run(check())
