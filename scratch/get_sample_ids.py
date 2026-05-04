import json

with open('frontend/public/mock-data/recruitments.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    ids = [str(item['id']) for item in data[:100]] # Get first 100 IDs
    
    # Ensure ID 25 is included if found elsewhere
    if "25" not in ids:
        for item in data:
            if str(item.get('id')) == "25":
                ids.append("25")
                break

    print(json.dumps(ids))
