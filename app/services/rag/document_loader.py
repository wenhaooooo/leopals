import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import fitz

from langchain_core.documents import Document


class CampusDocumentLoader:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _extract_metadata_from_path(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        file_name = path.name
        category = self._infer_category(file_name)

        return {
            "source": file_path,
            "file_name": file_name,
            "category": category,
            "file_type": path.suffix.lower(),
        }

    def _infer_category(self, file_name: str) -> str:
        file_name_lower = file_name.lower()
        if any(keyword in file_name_lower for keyword in ["kaoyan", "考研", "graduate", "postgraduate"]):
            return "考研"
        elif any(keyword in file_name_lower for keyword in ["calendar", "校历", "schedule", "timetable"]):
            return "校历"
        elif any(keyword in file_name_lower for keyword in ["policy", "政策", "regulation", "rule"]):
            return "政策"
        elif any(keyword in file_name_lower for keyword in ["course", "课程", "class"]):
            return "课程"
        elif any(keyword in file_name_lower for keyword in ["exam", "考试", "test"]):
            return "考试"
        else:
            return "校务"

    def _load_pdf_with_pymupdf(self, file_path: str) -> List[Document]:
        docs = []
        try:
            doc = fitz.open(file_path)
            base_metadata = self._extract_metadata_from_path(file_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():
                    metadata = base_metadata.copy()
                    metadata["page"] = page_num + 1
                    docs.append(Document(page_content=text, metadata=metadata))
            
            doc.close()
            return docs
        except Exception as e:
            raise RuntimeError(f"Failed to load PDF file {file_path}: {str(e)}")

    def _load_markdown_simple(self, file_path: str) -> List[Document]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            base_metadata = self._extract_metadata_from_path(file_path)
            
            docs = []
            metadata = base_metadata.copy()
            metadata["page"] = 1
            docs.append(Document(page_content=content, metadata=metadata))
            
            return docs
        except Exception as e:
            raise RuntimeError(f"Failed to load Markdown file {file_path}: {str(e)}")

    def _semantic_chunking(self, documents: List[Document]) -> List[Document]:
        chunked_docs = []
        for doc in documents:
            content = doc.page_content
            metadata = doc.metadata
            
            sentences = content.split('\n')
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                if current_length + sentence_length <= self.chunk_size:
                    current_chunk.append(sentence)
                    current_length += sentence_length
                else:
                    if current_chunk:
                        chunked_docs.append(
                            Document(
                                page_content='\n'.join(current_chunk),
                                metadata=metadata.copy()
                            )
                        )
                    current_chunk = [sentence]
                    current_length = sentence_length
            
            if current_chunk:
                chunked_docs.append(
                    Document(
                        page_content='\n'.join(current_chunk),
                        metadata=metadata.copy()
                    )
                )
        
        for i, chunked_doc in enumerate(chunked_docs):
            chunked_doc.metadata["chunk_index"] = i
        
        return chunked_docs

    def _load_file(self, file_path: str) -> List[Document]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._load_pdf_with_pymupdf(file_path)
        elif suffix in (".md", ".markdown"):
            return self._load_markdown_simple(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def load_and_split(self, file_path: str) -> List[Document]:
        docs = self._load_file(file_path)
        return self._semantic_chunking(docs)

    def load_directory(self, directory_path: str) -> List[Document]:
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Directory not found: {directory_path}")

        all_docs = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    docs = self._load_file(file_path)
                    split_docs = self._semantic_chunking(docs)
                    all_docs.extend(split_docs)
                except Exception as e:
                    continue

        return all_docs

    async def async_load_and_split(self, file_path: str) -> List[Document]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load_and_split, file_path)

    async def async_load_directory(self, directory_path: str) -> List[Document]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load_directory, directory_path)