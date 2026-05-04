
import json
import collections
from rich.console import Console
from rich.table import Table

console = Console()

def deep_verify(file_path):
    console.print(f"[bold blue]🔍 Deep Verification for: {file_path}[/bold blue]")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        console.print(f"[red]Failed to open file: {e}[/red]")
        return

    data = []
    for line in lines:
        try:
            data.append(json.loads(line))
        except:
            pass

    total_count = len(data)
    console.print(f"Total Records: [bold]{total_count}[/bold]")

    # 1. Duplicate Check
    instruction_hashes = [hash(d['instruction']) for d in data]
    input_hashes = [hash(d['input']) for d in data]
    output_hashes = [hash(d['output']) for d in data]
    
    dup_inst = total_count - len(set(instruction_hashes))
    dup_input = total_count - len(set(input_hashes))
    dup_output = total_count - len(set(output_hashes))

    console.print("\n[bold]1. Duplication Check[/bold]")
    if dup_inst == 0 and dup_input == 0 and dup_output == 0:
        console.print("[green]✅ No exact duplicates found in Instruction, Input, or Output.[/green]")
    else:
        console.print(f"[red]⚠️ Duplicates found: Inst({dup_inst}), Input({dup_input}), Output({dup_output})[/red]")

    # 2. Diversity Analysis
    roles = []
    companies = []
    
    # Simple extraction heuristics (since we don't have structured fields for these in 'metadata' for all records, 
    # but the current generation script puts them in metadata. Let's use metadata primarily)
    
    for d in data:
        meta = d.get('metadata', {})
        role = meta.get('job_role', 'Unknown')
        
        # Try to extract company from Input text if not in metadata explicitly (metadata doesn't have company field in generating script line 188, oh wait it is in input text)
        # Actually generate_dataset.py puts 'job_role' in metadata. 
        # But 'company' is embedded in 'input' text usually under [기업 분석 정보]
        
        roles.append(role)
        
        input_text = d.get('input', '')
        if '[기업 분석 정보]' in input_text:
            company_part = input_text.split('[기업 분석 정보]')[1].strip()
            # Extract first line or a few words as proxy for company
            company_name_proxy = company_part.split('\n')[0][:20] 
            companies.append(company_name_proxy)
        else:
            companies.append("Unknown")

    role_counts = collections.Counter(roles)
    company_counts = collections.Counter(companies)

    console.print("\n[bold]2. Diversity Top 5 (Roles)[/bold]")
    for r, c in role_counts.most_common(5):
        console.print(f"- {r}: {c}")

    console.print("\n[bold]2. Diversity Top 5 (Companies - Proxy)[/bold]")
    for r, c in company_counts.most_common(5):
        console.print(f"- {r}: {c}")

    # 3. Length & Quality Stats
    lengths = [len(d['output']) for d in data]
    avg_len = sum(lengths) / len(lengths)
    min_len = min(lengths)
    max_len = max(lengths)
    
    console.print("\n[bold]3. Output Length Stats[/bold]")
    console.print(f"Average: {avg_len:.1f} chars")
    console.print(f"Min: {min_len} chars")
    console.print(f"Max: {max_len} chars")
    
    # 4. Keyword Consistency (Simple)
    # Check if 'Java' in input implies 'Java' or 'Spring' or 'JVM' in output (just a random sample check)
    console.print("\n[bold]4. Semantic Consistency Spot Check (Random 3)[/bold]")
    import random
    samples = random.sample(data, 3)
    for i, s in enumerate(samples):
        inp = s['input'][:100].replace('\n', ' ')
        out = s['output'][:100].replace('\n', ' ')
        console.print(f"Sample {i+1}:")
        console.print(f"  Input: {inp}...")
        console.print(f"  Output: {out}...")

if __name__ == "__main__":
    deep_verify("../data/finetune/hcx_finetune_data.jsonl")
