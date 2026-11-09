"""Vector knowledge base: PDF ingestion + FAISS retrieval (Module 4/5: RAG)."""
import json
import logging
import threading
from pathlib import Path

from ..config import Settings
from ..errors import ValidationError

log = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, settings: Settings):
        self.s = settings
        self._lock = threading.Lock()
        self._embeddings = None
        self._index = None
        self._meta_path = settings.index_dir / "documents.json"
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # -- internals -------------------------------------------------------------------
    def _emb(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings

            self._embeddings = HuggingFaceEmbeddings(model_name=self.s.embedding_model)
        return self._embeddings

    def _load(self) -> None:
        if (self.s.index_dir / "index.faiss").exists():
            from langchain_community.vectorstores import FAISS

            # The index is created locally by this app only, so deserialisation is safe.
            self._index = FAISS.load_local(
                str(self.s.index_dir), self._emb(), allow_dangerous_deserialization=True
            )

    def _read_meta(self) -> dict[str, int]:
        if self._meta_path.exists():
            return json.loads(self._meta_path.read_text())
        return {}

    # -- public API ------------------------------------------------------------------
    def add_pdf(self, path: Path, display_name: str) -> int:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_community.vectorstores import FAISS
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        pages = PyPDFLoader(str(path)).load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.s.chunk_size, chunk_overlap=self.s.chunk_overlap
        )
        chunks = [c for c in splitter.split_documents(pages) if c.page_content.strip()]
        if not chunks:
            raise ValidationError("No extractable text found (is this a scanned PDF?).")
        for c in chunks:
            c.metadata["source"] = display_name
            c.metadata["page"] = int(c.metadata.get("page", 0)) + 1
        with self._lock:
            if self._index is None:
                self._index = FAISS.from_documents(chunks, self._emb())
            else:
                self._index.add_documents(chunks)
            self._index.save_local(str(self.s.index_dir))
            meta = self._read_meta()
            meta[display_name] = meta.get(display_name, 0) + len(chunks)
            self._meta_path.write_text(json.dumps(meta, indent=2))
        log.info("Indexed %s (%d chunks)", display_name, len(chunks))
        return len(chunks)

    def search(self, query: str, k: int | None = None):
        if self._index is None:
            return []
        with self._lock:
            return self._index.similarity_search(query, k=k or self.s.top_k)

    def documents(self) -> dict[str, int]:
        return self._read_meta()

    def has_documents(self) -> bool:
        return self._index is not None

    def clear(self) -> None:
        with self._lock:
            self._index = None
            for name in ("index.faiss", "index.pkl", "documents.json"):
                (self.s.index_dir / name).unlink(missing_ok=True)
