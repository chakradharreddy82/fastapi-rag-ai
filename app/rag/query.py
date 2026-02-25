from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import re
import time

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_mistralai import ChatMistralAI

from app.core.config import MISTRAL_API_KEY
from app.rag.guardrails import detect_guardrail_violation
from app.rag.tier_router import classify_tier
from app.core.metrics import metrics_store



class HelpDeskResponse(BaseModel):
    answer: str
    needsEscalation: bool
    targetTier: str
    severity: str
    reason: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str


router = APIRouter(prefix="/api")

DB_FAISS_PATH = "vectorstore/db_faiss"

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
)


def clean_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def severity_from_tier(tier: str) -> str:
    mapping = {
        "Tier 0": "LOW",
        "Tier 1": "MEDIUM",
        "Tier 2": "HIGH",
        "Tier 3": "CRITICAL",
    }
    return mapping.get(tier, "MEDIUM")


@router.post("/chat/", response_model=HelpDeskResponse)
async def ask_question(req: QuestionRequest):
    start_time = time.time()
    metrics_store.incr("requests_total")

    violation = detect_guardrail_violation(req.question)

    if violation:
        metrics_store.incr("guardrail_blocks")
        metrics_store.incr("escalations_triggered")

        latency_ms = (time.time() - start_time) * 1000
        metrics_store.record_latency(latency_ms)
        tier_info = classify_tier(req.question)
        target_tier = tier_info["tier"]
        needs_escalation = tier_info["needs_escalation"]

        return HelpDeskResponse(
            answer=(
                "I cannot assist with that request due to platform security "
                "and policy restrictions."
            ),
            needsEscalation=True,
            targetTier=target_tier,
            severity=severity_from_tier(target_tier),
            reason=f"Guardrail triggered: {violation['category']}",
        )

    if needs_escalation:
        metrics_store.incr("escalations_triggered")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    db = FAISS.load_local(
        DB_FAISS_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )

    llm = ChatMistralAI(
        api_key=MISTRAL_API_KEY,
        model="mistral-small-latest",
        temperature=0,
    )

    retriever = db.as_retriever(search_kwargs={"k": 6})

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
    )

    result = qa_chain.invoke({"question": req.question})
    clean_answer = clean_markdown(result["answer"])

    metrics_store.incr("successful_answers")

    latency_ms = (time.time() - start_time) * 1000
    metrics_store.record_latency(latency_ms)

    return HelpDeskResponse(
        answer=clean_answer,
        needsEscalation=needs_escalation,
        targetTier=target_tier,
        severity=severity_from_tier(target_tier),
        reason=None,
    )