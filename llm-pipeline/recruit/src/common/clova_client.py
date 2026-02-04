import os
import requests
import json
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

class ClovaStudioClient:
    def __init__(self):
        # .env 로드
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
        env_path = BASE_DIR / ".env"
        load_dotenv(dotenv_path=env_path)

        # API Key (User provided via .env)
        self.api_key = os.getenv("CLOVA_STUDIO_API_KEY")
        
        # API URL (Load from .env or fallback to v3 chat-completions)
        base_url = os.getenv("CLOVA_STUDIO_URL", "https://clovastudio.stream.ntruss.com")
        self.api_url = os.getenv("CLOVA_STUDIO_API_URL", f"{base_url}/v3/chat-completions/HCX-007")

    def get_headers(self) -> Dict[str, str]:
        # Based on reference file:
        # headers = {
        #     "Authorization": f"Bearer {self.ncp_api_key}",
        #     "Content-Type": "application/json",
        #     "Accept": "application/json"
        # }
        
        # However, if the key provided is a Test App key, it needs X-NCP-CLOVASTUDIO-API-KEY.
        # If it is a Service App key, it needs Bearer.
        # 'nv-...' keys are often for new HyperClova X Service Apps.
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def generate_content(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.5) -> str:
        headers = self.get_headers()
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "maxCompletionTokens": max_tokens,
            "temperature": temperature,
            "topP": 0.8,
            "topK": 0,
            "repeatPenalty": 5.0,
            "includeAiFilters": True
        }

        try:
            # Reference implementation uses non-streaming
            response = requests.post(self.api_url, headers=headers, json=payload, stream=False)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status", {}).get("code") == "20000":
                    return result.get("result", {}).get("message", {}).get("content", "")
                else:
                    print(f"Clova Studio API Error (Status Check): {result}")
                    return ""
            else:
                print(f"Clova Studio API Error: Status {response.status_code}, {response.text}")
                return response.status_code

        except Exception as e:
            print(f"Clova Studio API Error: {e}")
            return ""