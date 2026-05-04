import json
import os

def remap_mock_data():
    base_path = r'c:\Repo\pro-nlp-finalproject-nlp-01\frontend\public\mock-data'
    
    mapping = {
        "cover_letters": {
            "6": ["24", "37", "38", "39"],
            "7": ["35"],
            "8": ["18", "23", "34", "40"],
            "9": ["19", "20", "21", "22", "25", "26", "27", "28", "30", "31", "32", "33", "41"]
        },
        "portfolios": {
            "6": ["24", "37", "38", "39"],
            "7": ["35", "60", "61", "62", "63", "64", "66"],
            "8": ["18", "23", "34", "35", "39", "41", "42", "43", "44", "45", "46", "47", "48", "91", "92", "93", "94"],
            "9": ["19", "20", "21", "22", "25", "26", "27", "28", "30", "31", "32", "33", "37", "38", "49", "50", "51", "53", "54", "56", "58"]
        }
    }

    def get_target_user(item_id, item_type, current_user_id, title_or_name=""):
        for user_id, ids in mapping.get(item_type, {}).items():
            if str(item_id) in ids: return user_id
        if current_user_id in ["1", "2", "3", "4", "5"]:
            text = title_or_name.lower()
            if any(k in text for k in ["ios", "frontend", "ui", "react", "css"]): return "6"
            if any(k in text for k in ["backend", "spring", "infra", "server", "redis", "api"]): return "7"
            if any(k in text for k in ["data", "sql", "pipeline", "airflow", "ga4", "athena"]): return "8"
            if any(k in text for k in ["ai", "nlp", "llm", "ml", "transformer", "rag", "qa"]): return "9"
            return "9"
        return current_user_id

    # 1. Cover Letters
    cl_file = os.path.join(base_path, 'cover_letters.json')
    with open(cl_file, 'r', encoding='utf-8') as f: cls = json.load(f)
    for cl in cls: cl["user_id"] = get_target_user(cl["id"], "cover_letters", cl.get("user_id"), cl.get("title", ""))
    with open(cl_file, 'w', encoding='utf-8') as f: json.dump(cls, f, ensure_ascii=False, indent=2)

    # 2. Portfolios
    pf_file = os.path.join(base_path, 'portfolios.json')
    with open(pf_file, 'r', encoding='utf-8') as f: pfs = json.load(f)
    for pf in pfs: pf["user_id"] = get_target_user(pf["id"], "portfolios", pf.get("user_id"), pf.get("project_name", ""))
    with open(pf_file, 'w', encoding='utf-8') as f: json.dump(pfs, f, ensure_ascii=False, indent=2)

    # 3. Recommendations
    rc_file = os.path.join(base_path, 'recommendations.json')
    if os.path.exists(rc_file):
        with open(rc_file, 'r', encoding='utf-8') as f: recs = json.load(f)
        for rc in recs:
            text = str(rc.get("reason", "")).lower()
            if any(k in text for k in ["ios", "frontend", "ui"]): rc["user_id"] = "6"
            elif any(k in text for k in ["backend", "spring", "infra"]): rc["user_id"] = "7"
            elif any(k in text for k in ["data", "sql", "pipeline", "ga4"]): rc["user_id"] = "8"
            elif any(k in text for k in ["ai", "nlp", "llm", "ml"]): rc["user_id"] = "9"
        with open(rc_file, 'w', encoding='utf-8') as f: json.dump(recs, f, ensure_ascii=False, indent=2)

    # 4. Notifications
    nt_file = os.path.join(base_path, 'notifications.json')
    with open(nt_file, 'r', encoding='utf-8') as f: nts = json.load(f)
    updated_cls = {str(c["id"]): c["user_id"] for c in cls}
    updated_pfs = {str(p["id"]): p["user_id"] for p in pfs}
    for nt in nts:
        link = nt.get("link", "")
        if "/my/cover-letters/" in link:
            cid = link.split("/")[-1]
            if cid in updated_cls: nt["user_id"] = updated_cls[cid]
        elif "/my/portfolios/" in link:
            pid = link.split("/")[-1]
            if pid in updated_pfs: nt["user_id"] = updated_pfs[pid]
    with open(nt_file, 'w', encoding='utf-8') as f: json.dump(nts, f, ensure_ascii=False, indent=2)

    print("Remapping complete.")

if __name__ == "__main__":
    remap_mock_data()
