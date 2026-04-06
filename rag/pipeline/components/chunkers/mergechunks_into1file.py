import json
import os

PROCESSED_DIR = "./data/processed/medication_files"

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

    master_path = os.path.join(PROCESSED_DIR, "all_medicine_chunks.json")
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Merged {len(files)} files → {len(all_chunks)} total chunks")
    print(f"   Saved to: {master_path}")

if __name__ == "__main__":
    merge_all_chunks()