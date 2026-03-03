import uuid
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)


def create_ticket_record(
    question: str,
    answer: str,
    tier: str,
    severity: str,
    needs_escalation: bool,
    execution_time_ms: float,
) -> str:
    ticket_id = f"INC-{str(uuid.uuid4())[:8].upper()}"

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into helpdesk_tickets
                (id, question, answer, target_tier, severity,
                 needs_escalation, execution_time_ms)
                values
                (:id, :question, :answer, :tier, :severity,
                 :needs_escalation, :execution_time_ms)
                """
            ),
            {
                "id": ticket_id,
                "question": question,
                "answer": answer,
                "tier": tier,
                "severity": severity,
                "needs_escalation": needs_escalation,
                "execution_time_ms": execution_time_ms,
            },
        )

    return ticket_id


def get_ticket(ticket_id: str):
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                select *
                from helpdesk_tickets
                where id = :id
                """
            ),
            {"id": ticket_id},
        ).mappings().first()

    return result