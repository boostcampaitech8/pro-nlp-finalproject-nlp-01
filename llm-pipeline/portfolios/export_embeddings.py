import json
import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def export_embeddings():
    # Location of the embedding vectors
    persist_base_dir = Path(__file__).parent.parent / "self_introduction" / "embeddings" / "chroma_db"
    
    if not persist_base_dir.exists():
        print(f"Error: Embedding directory not found at {persist_base_dir}")
        return

    embedding_model_name = "jhgan/ko-sroberta-multitask"
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    all_data = {}
    
    # Iterate through all user collections
    for collection_path in persist_base_dir.iterdir():
        if collection_path.is_dir():
            collection_name = collection_path.name
            print(f"Exporting collection: {collection_name}...")
            
            try:
                vectorstore = Chroma(
                    collection_name=collection_name,
                    embedding_function=embeddings,
                    persist_directory=str(collection_path)
                )
                
                raw_data = vectorstore.get()
                documents = []
                
                for i in range(len(raw_data['ids'])):
                    documents.append({
                        "id": raw_data['ids'][i],
                        "content": raw_data['documents'][i],
                        "metadata": raw_data['metadatas'][i]
                    })
                
                # Sort documents by project_name and chunk_index for readability
                documents.sort(key=lambda x: (
                    x['metadata'].get('project_name', ''), 
                    x['metadata'].get('chunk_index', 0)
                ))
                
                all_data[collection_name] = documents
                
                # Output JSON in the SAME location as the vectors (inside the collection folder)
                output_path = collection_path / f"export_{collection_name}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(documents, f, indent=2, ensure_ascii=False)
                print(f"  -> Saved to {output_path}")

            except Exception as e:
                print(f"  -> Failed to export {collection_name}: {e}")

    # Also save a consolidated file in the base embeddings directory
    consolidated_path = persist_base_dir / "all_portfolios_export.json"
    with open(consolidated_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print(f"\nConsolidated export saved to: {consolidated_path}")

if __name__ == "__main__":
    export_embeddings()
