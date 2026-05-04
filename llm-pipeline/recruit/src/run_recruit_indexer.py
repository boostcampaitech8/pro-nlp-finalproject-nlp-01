import json
import os
from pathlib import Path
from recruit_indexer import RecruitIndexer

# Path to the data file
RECRUIT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = RECRUIT_ROOT / "data" / "recruit_data" / "final_recruitment_all_items.json"

def main():
    if not DATA_FILE.exists():
        print(f"Error: Data file not found at {DATA_FILE}")
        return

    print(f"Loading data from {DATA_FILE}...")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    print(f"Loaded {len(data)} items.")

    indexer = RecruitIndexer()
    
    print("Creating vector store (this may take a while)...")
    try:
        # Increase batch size via underlying mechanism if needed, but for <50 items it's fine
        vectorstore = indexer.create_vectorstore(data)
        print("Vector store created successfully.")
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return

    # Optional: Verify with a search
    query = "백엔드 개발자"
    print(f"\nVerifying with query: '{query}'")
    results = indexer.search_recruitments(query, k=3)
    
    print(f"\nFound {len(results)} results:")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.metadata.get('company')} - {doc.metadata.get('title')}")
        print(f"   Link: {doc.metadata.get('link')}")

if __name__ == "__main__":
    main()
