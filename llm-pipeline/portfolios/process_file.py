import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from src.extractors.file_extractor import FileExtractor
from src.processors.llm_refiner import LLMRefiner
from src.storage.vector_store import PortfolioVectorStore

def main():
    parser = argparse.ArgumentParser(description="Process Local File Portfolio")
    parser.add_argument("--path", required=True, help="Path to the PDF or Image file")
    args = parser.parse_args()

    print(f"--- Step 1: Extracting from file ({args.path}) ---")
    extractor = FileExtractor()
    raw_text = extractor.extract(args.path)
    
    if not raw_text or "Error" in raw_text:
        print(f"Extraction Failed: {raw_text}")
        return
    
    print(f"Extracted Text (first 200 chars):\n{raw_text[:200]}...\n")

    print("--- Step 2: Refining text with LLM ---")
    try:
        refiner = LLMRefiner()
        combined_result = refiner.extract_user_data_and_queries(raw_text)
        print(f"Refinement Successful. Extracted {len(combined_result.user_data.projects)} projects.")
    except Exception as e:
        print(f"Refinement Failed: {e}")
        return

    print("--- Step 3: Embedding and Storing ---")
    try:
        vector_store = PortfolioVectorStore()
        metadata = {"source": args.path, "type": "file"}
        vector_store.save(combined_result, metadata)
        print("Done! Data stored in Chroma DB.")
    except Exception as e:
        print(f"Storage Failed: {e}")

if __name__ == "__main__":
    main()
