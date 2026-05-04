import json
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PortfolioVectorStore:
    """Manages embedding storage in Chroma DB."""

    def __init__(self, persist_dir: str = None):
        # Default path aligned with self_introduction
        if persist_dir:
            self.persist_base_dir = Path(persist_dir)
        else:
            # Match self_introduction/embeddings/chroma_db
            self.persist_base_dir = Path(__file__).parent.parent.parent.parent / "self_introduction" / "embeddings" / "chroma_db"
            
        self.embedding_model_name = "jhgan/ko-sroberta-multitask"
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Chunking settings aligned with self_introduction
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " "]
        )

    def save(self, combined_result, source_metadata: dict) -> None:
        """
        Parses CombinedResult, chunks project descriptions, and saves to Chroma DB with specific metadata.
        """
        user_data = combined_result.user_data
        profile = user_data.profile
        user_id = profile.user_id or "unknown_user"
        user_name = profile.name or "Unknown"
        
        collection_name = f"user_{user_id}"
        persist_directory = self.persist_base_dir / collection_name
        
        # Save refined structured data (including search queries) to JSON before chunking
        self._save_to_json(combined_result, persist_directory, collection_name)

        all_docs = []
        
        for project in user_data.projects:
            project_name = project.project_name
            full_description = project.description_for_embedding or ""
            tech_stack = project.tech_stack
            role = project.role or ""
            period = project.period or ""
            
            if not full_description:
                continue
                
            # Chunking
            chunks = self.text_splitter.split_text(full_description)
            
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": "user_portfolio",
                    "source_path": source_metadata.get("source", ""),
                    "source_type": source_metadata.get("type", ""),
                    "user_id": user_id,
                    "user_name": user_name,
                    "project_name": project_name,
                    "tech_stack": ", ".join(tech_stack),
                    "role": role,
                    "period": period,
                    "chunk_index": i,
                    "full_context": full_description
                }
                all_docs.append(Document(page_content=chunk, metadata=metadata))
        
        if not all_docs:
            print("No project descriptions found to store.")
            return

        print(f"Storing {len(all_docs)} chunks in Chroma DB collection '{collection_name}' at {persist_directory}...")
        
        Chroma.from_documents(
            documents=all_docs,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=str(persist_directory)
        )

    def _save_to_json(self, combined_result, directory: Path, collection_name: str) -> None:
        """Saves the structured user data and job queries to a JSON file before chunking."""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            output_file = directory / f"refined_{collection_name}.json"
            
            # Convert Pydantic model to dict
            data_dict = combined_result.model_dump()
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            print(f"Refined structured data and queries saved to {output_file}")
        except Exception as e:
            print(f"Warning: Failed to save refined JSON: {e}")
