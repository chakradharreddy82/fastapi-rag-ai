from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import re
import time

from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_community.vectorstores import PGVector
from app.services.ticket_service import create_ticket_record, get_ticket
from app.rag.guardrails import detect_guardrail_violation
from app.rag.tier_router import classify_tier
from app.core.metrics import metrics_store
from app.core.config import DATABASE_URL, MISTRAL_API_KEY

router = APIRouter(prefix="/api")

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
)


class HelpDeskResponse(BaseModel):
    answer: str
    needsEscalation: bool
    targetTier: str
    severity: str
    reason: Optional[str] = None
    ticketId: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str


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

    clean_answer = ""

    violation = detect_guardrail_violation(req.question)
    ticket_match = re.search(r"INC-[A-Z0-9]+", req.question.upper())
    if ticket_match:
        ticket_id = ticket_match.group(0)
        ticket = get_ticket(ticket_id)

        if ticket:
            return HelpDeskResponse(
                answer=(
                    f"Ticket {ticket_id} details:\n"
                    f"Question: {ticket['question']}\n"
                    f"Tier: {ticket['target_tier']}\n"
                    f"Severity: {ticket['severity']}\n"
                    f"Execution Time: {round(ticket['execution_time_ms'],2)} ms"
                ),
                needsEscalation=False,
                targetTier=ticket["target_tier"],
                severity=ticket["severity"],
                reason="Ticket lookup",
            )
        else:
            return HelpDeskResponse(
                answer=f"Ticket {ticket_id} not found.",
                needsEscalation=False,
                targetTier="Tier 0",
                severity="LOW",
            )

    tier_info = classify_tier(req.question)
    target_tier = tier_info["tier"]
    needs_escalation = tier_info["needs_escalation"]

    if violation:
        metrics_store.incr("guardrail_blocks")
        metrics_store.incr("escalations_triggered")

        return HelpDeskResponse(
            answer="I cannot assist with that request due to platform security and policy restrictions.",
            needsEscalation=True,
            targetTier=target_tier,
            severity=severity_from_tier(target_tier),
            reason=f"Guardrail triggered: {violation['category']}",
        )

    if needs_escalation:
        metrics_store.incr("escalations_triggered")

    embeddings = MistralAIEmbeddings(
        model="mistral-embed",
        api_key=MISTRAL_API_KEY,
    )

    db = PGVector(
        connection_string=DATABASE_URL,
        embedding_function=embeddings,
        collection_name="rag_docs",
    )

    retriever = db.as_retriever(search_kwargs={"k": 6})

    llm = ChatMistralAI(
        api_key=MISTRAL_API_KEY,
        model="mistral-small-latest",
        temperature=0,
    )

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

    ticket_id = None

    if needs_escalation:
        metrics_store.incr("escalations_triggered")

        ticket_id = create_ticket_record(
            question=req.question,
            answer=clean_answer,
            tier=target_tier,
            severity=severity_from_tier(target_tier),
            needs_escalation=needs_escalation,
            execution_time_ms=latency_ms,
        )

    final_answer = clean_answer

    if ticket_id:
        final_answer += f"\n\nSupport ticket created: {ticket_id}"

    return HelpDeskResponse(
        answer=final_answer,
        needsEscalation=needs_escalation,
        targetTier=target_tier,
        severity=severity_from_tier(target_tier),
        reason=None,
        ticketId=ticket_id,
    )