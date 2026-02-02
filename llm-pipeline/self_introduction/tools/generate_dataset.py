import argparse
import sys
import json
import time
from pathlib import Path
from rich.console import Console

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import MODEL_ID_GEMINI, MODEL_ID_DEEPSEEK, DATA_DIR
from src.finetune.generator import FinetuneDataGenerator
from src.finetune.comparison import run_model_comparison
from src.finetune.input_generator import InputGenerator

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Finetuning Data Generator CLI")
    parser.add_argument("mode", choices=["compare", "generate"], help="Mode (compare: A/B Test, generate: Create Dataset)")
    parser.add_argument("--count", type=int, default=100, help="Number of samples to generate (default: 100)")
    args = parser.parse_args()
    
    # 생성기 초기화 (변경: DeepSeek로 선정)
    generator = FinetuneDataGenerator(model_id=MODEL_ID_DEEPSEEK)
    
    if args.mode == "compare":
        # 공통 시스템 프롬프트 (링커리어 합격 자소서 스타일)
        base_system_prompt = (
            "당신은 IT 기업 합격 자소서 전문 작가입니다.\n"
            "링커리어(Linkcareer)의 합격 자소서들처럼 다음 원칙을 반드시 지켜 작성하세요:\n"
            "1. 문항 시작 시 [이곳에 핵심 성과를 담은 소제목]을 대괄호 안에 작성하세요.\n"
            "2. 본문에는 ###, **, - 같은 마크다운 기호를 절대 사용하지 마세요. (순수 텍스트만 사용)\n"
            "3. [Situation], [Action] 같은 태그를 절대 쓰지 마세요. 자연스러운 줄글(Narrative)로 문단을 나누어 서술하세요.\n"
            "4. 기술적 전문성이 드러나도록 구체적인 기술 스택과 수치(%)를 문장 속에 자연스럽게 녹여내세요.\n"
            "5. AI가 쓴 것 같지 않은, 지원자의 진솔한 경험이 느껴지는 어조를 유지하세요."
        )

        test_cases = [
            {
                "system": base_system_prompt,
                "user": "지원분야: 백엔드 개발\n문항: 지원동기 (800자 이내)\n소재: 비전공자로서 개발에 흥미를 느낌. 오픈소스 프로젝트 참여 경험. 대규모 트래픽 처리 기술에 관심 많음."
            },
            {
                "system": base_system_prompt,
                "user": "지원분야: 프론트엔드\n문항: 협업 중 갈등 해결 경험\n소재: 디자이너와 UI 구현 방식 차이로 대립. 기술적 제약을 쉽게 설명하고 대안 제시하여 설득함."
            },
            {
                "system": f"{base_system_prompt}\n추가 지시: 사용자의 거친 메모를 전문가가 수정한 것처럼 기술적 깊이를 더해 재작성하세요.",
                "user": "직무: AI 엔지니어\n내용: 모델 성능이 안 좋아서 데이터 전처리를 다시 했다. 그랬더니 정확도가 10% 올랐다.\n요청: 이 내용을 구체적인 수치와 기술 용어를 사용해 전문적으로 바꿔줘."
            }
        ]
        
        output_file = project_root / "output" / "model_comparison.md"
        
        run_model_comparison(
            generator=generator,
            other_model_id=MODEL_ID_DEEPSEEK,
            test_cases=test_cases,
            output_path=output_file
        )
        
    elif args.mode == "generate":
        import os
        
        # 1. 시나리오 생성 단계 생략 (자율 생성 모드)
        console.print("[bold cyan]Step: DeepSeek 자율 생성 모드로 100개 데이터셋 구축 시작[/bold cyan]")
        
        # 중간 저장
        save_dir = Path(DATA_DIR) / "finetune"
        save_dir.mkdir(parents=True, exist_ok=True)
        # raw_inputs.json 저장은 이제 필요 없음 (자율 생성으로 바로 데이터셋 생성)

        # [최종 확정] 자율형 다양성 프롬프트
        system_prompt = (
            "당신은 대한민국 최고 수준의 IT 채용 전문가이자 학습 데이터 생성기입니다.\n"
            "당신의 목표는 HyperCLOVA X를 파인튜닝하기 위한 '다양하고 현실적인' 자소서 데이터셋을 만드는 것입니다.\n\n"
            "다음 과정을 거쳐 고품질 데이터 1세트를 생성하세요:\n"
            "0. 직무/페르소나 선정: 다양한 산업군과 기업 규모를 고려하여 무작위로 선정하세요.\n"
            "   - **포함 대상**: IT 대기업(네이버, 카카오, 라인), 유니콘(쿠팡, 토스, 배달의민족, 당근, 야놀자), 게임(넥슨, 크래프톤, 펄어비스, 인디게임사), 전자/제조(삼성전자, LG전자, 현대차), 금융(KB국민은행, 신한카드, 핀테크), AI 스타트업(몰로코, 업스테이지, 뤼이드), 이커머스/물류(마켓컬리, 무신사, CJ대한통운) 등.\n"
            "   - **주의**: 유명한 '네카쿠배'에만 편중되지 않도록, 중견기업이나 성장하는 스타트업도 적극 포함하세요.\n"
            "   - **직무 범위**: 백엔드, 프론트엔드, 안드로이드/iOS, AI/ML, 데이터 엔지니어, DevOps/SRE, 보안, PM/PO, UI/UX 디자인 등 다양한 직무를 골고루 생성하세요.\n"
            "1. 문항 생성: 해당 전문가의 실제 기출 스타일 문항을 생성하고, 반드시 글자 수 제한(예: 800자 이내)을 포함하세요.\n"
            "2. 답변 작성 (Deep Reality):\n"
            "   - **The Struggle**: 성공담보다는 해결 전의 '막막함', '기술적 난관', '의견 대립' 등 인간적인 고민 과정을 집요하게 서술하세요.\n"
            "   - **Structural Diversity**: 'STAR(배경-직무-행동-결과)', '문제-가설-검증-결론', '성과 위주 두괄식' 등 구조를 매번 다르게 변주하세요.\n"
            "   - **Tone Monitoring**: '팀이 숙연해졌다', '참사' 같은 과도하게 감상적인 표현을 지양하고, 현직자의 담백하고 전문적인 문체를 유지하세요.\n"
            "   - 마크다운 기호(###, **) 절대 사용 금지 (순수 텍스트만).\n"
            "   - 구체적인 정량 지표와 기술 용어를 반드시 포함하세요.\n"
            "3. RAG 컨텍스트 생성 (Input): \n"
            "   - 위 답변을 작성하기 위해 참고했을 법한 '원천 데이터(Source Data)'를 역으로 생성하세요.\n"
            "   - [핵심 경험 요약]: 지원자의 이력서나 포트폴리오에 적혀있을 법한 핵심 성과 요약 (개조식)\n"
            "   - [기업 분석 정보]: 지원하는 기업의 인재상이나 기술 스택 등 답변에 녹여낸 배경 정보\n\n"
            "출력 형식:\n"
            "[직무]: {선정한 직무}\n"
            "[연차]: {신입/경력/N년차}\n"
            "[구조]: {선택한 답변 구조 템플릿 명칭}\n"
            "[문항]: {생성된 질문}\n"
            "[핵심경험]: {자소서의 바탕이 된 경험 소재 요약 (3~4줄)}\n"
            "[기업정보]: {자소서에 반영된 기업/직무 정보 (1~2줄)}\n"
            "[답변]: {생성된 자소서}"
        )

        # 직무 리스트 (다양성 확보를 위해 확장 가능)
        roles = [
            "백엔드 개발자", "프론트엔드 개발자", "데이터 엔지니어", "AI/ML 엔지니어", 
            "인프라/DevOps 엔지니어", "서비스 기획자", "UX 디자이너", "데이터 분석가",
            "Android/iOS 앱 개발자", "보안 엔지니어"
        ]

        # 1. 기존 진행 상황 확인 (Resume 로직)
        output_path = save_dir / "hcx_finetune_data.jsonl"
        existing_count = 0
        if output_path.exists():
            with open(output_path, "r", encoding="utf-8") as f:
                existing_count = sum(1 for _ in f)
        
        if existing_count >= args.count:
            console.print(f"[yellow]⚠️ 이미 {existing_count}개의 데이터가 존재합니다. 생성을 종료합니다.[/yellow]")
            return

        if existing_count > 0:
            console.print(f"[yellow]🔄 기존에 생성된 {existing_count}개의 데이터를 이어서 생성합니다. ({existing_count + 1}번부터 시작)[/yellow]")

        console.print(f"🚀 총 {args.count - existing_count}개의 무작위 직무 자소서 데이터를 생성을 시작합니다...")
        
        for i in range(existing_count, args.count):
            user_input = "무작위 IT/신산업 직군의 고품질 자소서 데이터 1세트를 생성하세요."
            
            console.print(f"[{i+1}/{args.count}] 무작위 직무 데이터 생성 중...")
            result = generator.generate_completion(system_prompt, user_input, temperature=0.9) # 다양성 위해 온도를 살짝 높임
            
            if result:
                try:
                    # [직무], [연차], [구조], [문항], [핵심경험], [기업정보], [답변] 파싱
                    # 파싱 로직을 더 견고하게 분리
                    chunks = {}
                    current_key = None
                    for line in result.split('\n'):
                        line = line.strip()
                        if line.startswith('[직무]:'): chunks['role'] = line.replace('[직무]:', '').strip()
                        elif line.startswith('[연차]:'): chunks['seniority'] = line.replace('[연차]:', '').strip()
                        elif line.startswith('[구조]:'): chunks['template'] = line.replace('[구조]:', '').strip()
                        elif line.startswith('[문항]:'): 
                            current_key = 'question'
                            chunks[current_key] = line.replace('[문항]:', '').strip()
                        elif line.startswith('[핵심경험]:'): 
                            current_key = 'experience'
                            chunks[current_key] = line.replace('[핵심경험]:', '').strip()
                        elif line.startswith('[기업정보]:'): 
                            current_key = 'company_info'
                            chunks[current_key] = line.replace('[기업정보]:', '').strip()
                        elif line.startswith('[답변]:'): 
                            current_key = 'answer'
                            chunks[current_key] = line.replace('[답변]:', '').strip()
                        elif current_key and line: # 멀티라인 처리
                             chunks[current_key] += "\n" + line

                    # 필수 필드 확인
                    required_keys = ['role', 'question', 'experience', 'company_info', 'answer']
                    if not all(k in chunks for k in required_keys):
                        console.print(f"[yellow]⚠️ 필수 필드 누락으로 스킵: {list(chunks.keys())}[/yellow]")
                        continue
                    
                    role_part = chunks['role']
                    seniority_part = chunks.get('seniority', 'N/A')
                    structure_part = chunks.get('template', 'N/A')
                    question = chunks['question']
                    experience = chunks['experience']
                    company_info = chunks['company_info']
                    answer = chunks['answer']
                    
                    # 글자 수 계산
                    char_count = len(answer)
                    
                    # RAG 시뮬레이션 Input 생성
                    rag_input_context = (
                        f"지원 직무: {role_part}\n"
                        f"[핵심 경험 요약]\n{experience}\n\n"
                        f"[기업 분석 정보]\n{company_info}"
                    )
                    
                    data_entry = {
                        "instruction": f"문항: {question}",
                        "input": rag_input_context,
                        "output": answer,
                        "metadata": {
                            "job_role": role_part,
                            "seniority": seniority_part,
                            "template": structure_part,
                            "char_count": char_count,
                            "model_id": generator.model_id
                        }
                    }
                    
                    # 즉시 저장 (Append 모드)
                    with open(output_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(data_entry, ensure_ascii=False) + "\n")
                except Exception as e:
                    console.print(f"❌ 파싱 오류 발생: {e}")
                    continue
            
            # API 레이트 리미트 방지
            time.sleep(0.5)

        console.print(f"✅ 모든 작업 완료! 최종 데이터셋: {output_path}")

if __name__ == "__main__":
    main()
