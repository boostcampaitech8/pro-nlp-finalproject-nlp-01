from pathlib import Path
from rich.console import Console
from rich.table import Table
from .generator import FinetuneDataGenerator

console = Console()

def run_model_comparison(generator: FinetuneDataGenerator, 
                        other_model_id: str,
                        test_cases: list, 
                        output_path: Path):
    """
    A/B 테스트 실행 및 리포트 생성
    """
    console.print(f"[bold]🚀 Starting A/B Test:[/bold] {generator.model_id} vs {other_model_id}")
    
    report_content = f"# Model Comparison Report\n\n"
    report_content += f"**Date**: {Path(output_path).stem}\n"
    report_content += f"**Model A**: {generator.model_id}\n"
    report_content += f"**Model B**: {other_model_id}\n\n"
    report_content += "---\n\n"
    
    for i, case in enumerate(test_cases, 1):
        system_prompt = case.get("system", "You are a helpful assistant.")
        user_prompt = case.get("user", "")
        
        console.print(f"Generating Case {i}...")
        
        results = generator.compare_models(
            other_model_id=other_model_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        result_a = results[generator.model_id]
        result_b = results[other_model_id]
        
        # Markdown 리포트 작성
        report_content += f"## Case {i}\n"
        report_content += f"**User Prompt**:\n> {user_prompt}\n\n"
        
        report_content += f"### Model A ({generator.model_id})\n"
        report_content += f"{result_a}\n\n"
        
        report_content += f"### Model B ({other_model_id})\n"
        report_content += f"{result_b}\n\n"
        
        report_content += "---\n\n"
        
    # 파일 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    console.print(f"[bold green]✓ Report saved to:[/bold green] {output_path}")
