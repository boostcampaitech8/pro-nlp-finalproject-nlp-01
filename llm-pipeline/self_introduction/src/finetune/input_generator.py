import json
from pathlib import Path
from typing import List, Dict
from rich.console import Console
from .generator import FinetuneDataGenerator

console = Console()

class InputGenerator:
    def __init__(self, generator: FinetuneDataGenerator):
        self.generator = generator
        self.roles = ["백엔드 신입/주니어", "프론트엔드 신입/주니어", "AI/ML 엔지니어", "DevOps/인프라", "데이터 엔지니어"]
        self.topics = ["지원동기", "프로젝트 핵심 기술 경험", "기술적 난제 해결(Troubleshooting)", "팀 협업 및 갈등 해결", "성장 과정 및 가치관"]

    def brainstorm_scenarios(self, role: str, topic: str, count: int = 4) -> List[Dict]:
        """
        특정 직무와 주제에 대해 가상의 '거친 메모(Raw Experience)'를 생성
        """
        system_prompt = (
            "당신은 IT 채용 데이터 생성 전문가입니다. "
            "지원자가 자신의 경험을 일기나 메모장에 대충 적어놓은 듯한 '거친 소재 리스트'를 만들어주세요."
        )
        
        user_prompt = (
            f"직무: {role}\n"
            f"주제: {topic}\n"
            f"수량: {count}개\n\n"
            "각 항목은 다음 JSON 형식을 포함한 리스트로 응답하세요:\n"
            "[\n"
            "  {\n"
            "    \"role\": \"직무명\",\n"
            "    \"topic\": \"주제명\",\n"
            "    \"raw_experience\": \"여기에 거칠게 요약된 경험 소재 내용 (메모 형식으로 2~3문장)...\"\n"
            "  }\n"
            "]\n"
            "JSON 외의 다른 텍스트는 응답하지 마세요."
        )

        response = self.generator.generate_completion(system_prompt, user_prompt, temperature=0.8)
        
        try:
            # 코드 블록 제어 (LLM이 ```json 을 붙이는 경우 대비)
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if clean_response.startswith("json"):
                clean_response = clean_response[4:].strip()
                
            return json.loads(clean_response)
        except Exception as e:
            console.print(f"[red]Error parsing scenarios for {role}-{topic}: {e}[/red]")
            return []

    def generate_all(self, total_count: int = 100) -> List[Dict]:
        all_scenarios = []
        samples_per_pair = 4 # 5 roles * 5 topics * 4 = 100
        
        for role in self.roles:
            for topic in self.topics:
                console.print(f"[cyan]Brainstorming:[/cyan] {role} - {topic}...")
                pair_scenarios = self.brainstorm_scenarios(role, topic, samples_per_pair)
                all_scenarios.extend(pair_scenarios)
                
        return all_scenarios[:total_count]
