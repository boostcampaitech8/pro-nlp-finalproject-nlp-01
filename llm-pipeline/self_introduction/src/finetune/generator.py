import os
import json
import time
from typing import List, Dict, Optional
import openai
from dotenv import load_dotenv
from rich.console import Console

from config.settings import (
    OPENROUTER_API_KEY, 
    OPENROUTER_BASE_URL,
    MODEL_ID_GEMINI,
    MODEL_ID_DEEPSEEK
)

# 로거 설정
console = Console()

class FinetuneDataGenerator:
    def __init__(self, model_id: str = MODEL_ID_GEMINI):
        """
        초기화
        :param model_id: 사용할 모델 ID (기본값: Gemini)
        """
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY가 설정되지 않았습니다.")
            
        self.client = openai.OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        self.model_id = model_id
        console.print(f"[bold green]Model Initialized:[/bold green] {self.model_id}")

    def generate_completion(self, 
                          system_prompt: str, 
                          user_prompt: str,
                          temperature: float = 0.7,
                          max_tokens: int = 2000) -> Optional[str]:
        """
        OpenRouter API를 통해 텍스트 생성
        """
        try:
            console.print(f"[dim]Sending request to {self.model_id}...[/dim]")
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=60.0  # 타임아웃 60초 설정
            )
            
            duration = time.time() - start_time
            console.print(f"[dim]Response received from {self.model_id} ({duration:.1f}s)[/dim]")
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[bold red]Error requesting {self.model_id}:[/bold red] {str(e)}")
            return None

    def compare_models(self, 
                      other_model_id: str, 
                      system_prompt: str, 
                      user_prompt: str) -> Dict[str, str]:
        """
        두 모델의 결과를 비교 생성
        """
        # 현재 모델(A) 생성
        result_a = self.generate_completion(system_prompt, user_prompt)
        
        # 비교 모델(B) 생성 (일시적으로 클라이언트 생성 또는 ID 변경)
        original_model = self.model_id
        self.model_id = other_model_id
        result_b = self.generate_completion(system_prompt, user_prompt)
        self.model_id = original_model # 복구
        
        return {
            original_model: result_a,
            other_model_id: result_b
        }
