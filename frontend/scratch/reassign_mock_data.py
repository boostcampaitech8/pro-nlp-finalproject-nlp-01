import json

def reassign_to_demo_user():
    cl_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letters.json'
    items_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\cover_letter_items.json'
    notif_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data\notifications.json'
    
    DEMO_USER_ID = "6"
    TARGET_CL_IDS = ["26", "31", "32", "33", "38"]

    # Update Cover Letters
    with open(cl_path, 'r', encoding='utf-8') as f:
        cls = json.load(f)
    for cl in cls:
        if cl["id"] in TARGET_CL_IDS:
            cl["user_id"] = DEMO_USER_ID
    with open(cl_path, 'w', encoding='utf-8') as f:
        json.dump(cls, f, ensure_ascii=False, indent=2)

    # Update Notifications for these CLs
    with open(notif_path, 'r', encoding='utf-8') as f:
        notifs = json.load(f)
    for n in notifs:
        # If notification link points to one of our target CLs, assign to demo user
        for cl_id in TARGET_CL_IDS:
            if f"/cover-letters/{cl_id}" in n.get("link", ""):
                n["user_id"] = DEMO_USER_ID
    with open(notif_path, 'w', encoding='utf-8') as f:
        json.dump(notifs, f, ensure_ascii=False, indent=2)

reassign_to_demo_user()
