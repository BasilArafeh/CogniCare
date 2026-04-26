import json
import os

PROCESSED_DIR = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medication_files_cleaned/seperate_chunks"
OUTPUT_DIR = "/Users/leensalman/Desktop/gp2/CogniCare/rag/data/processed/medication_files_cleaned/all_chunks"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def merge_all_chunks():
    files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith("_chunks.json")]

    if not files:
        print(f"No chunk files found in {PROCESSED_DIR}")
        return

    all_chunks = []

    for filename in files:
        filepath = os.path.join(PROCESSED_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        all_chunks.extend(chunks)

    master_path = os.path.join(OUTPUT_DIR, "all_medicine_chunks.json")
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Merged {len(files)} files → {len(all_chunks)} total chunks")
    print(f"   Saved to: {master_path}")

if __name__ == "__main__":
    merge_all_chunks()