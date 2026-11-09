"""Conversational RAG answer chain with citations (Module 4: RAG + Groq)."""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..llm import text_of

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You answer questions using ONLY the provided context from the user's documents. "
            "If the answer is not in the context, say you could not find it in the documents. "
            "Be concise and cite sources as [file p.N].\n\nContext:\n{context}",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


def format_context(docs) -> str:
    return "\n\n".join(
        f"[{d.metadata.get('source', '?')} p.{d.metadata.get('page', '?')}]\n{d.page_content}"
        for d in docs
    )


def sources_of(docs) -> list[dict]:
    seen, out = set(), []
    for d in docs:
        key = (d.metadata.get("source"), d.metadata.get("page"))
        if key not in seen:
            seen.add(key)
            out.append({"source": key[0], "page": key[1]})
    return out


def answer_from_docs(llm, question: str, history: list[tuple[str, str]], docs) -> dict:
    if not docs:
        return {
            "answer": "No documents are indexed yet. Upload a PDF first.",
            "sources": [],
        }
    msg = (PROMPT | llm).invoke(
        {"context": format_context(docs), "history": history, "question": question}
    )
    return {"answer": text_of(msg), "sources": sources_of(docs)}
