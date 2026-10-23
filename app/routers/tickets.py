from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, MessageCreate,
    AssignTicket, StatusUpdate, TicketOut, MessageOut
)
# Импортируем функцию получения текущего пользователя из вашего auth.py
from app.routers.auth import get_current_user

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketOut)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "customer":
        raise HTTPException(403, "Customers only")
    ticket = Ticket(**data.model_dump(), owner_id=user.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/", response_model=list[TicketOut])
def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(Ticket)

    if user.role == "customer":
        query = query.filter(Ticket.owner_id == user.id)
    elif user.role == "support":
        query = query.filter(Ticket.assigned_to == user.id)
    elif user.role != "admin":
        raise HTTPException(403, "Forbidden")

    if status is not None:
        if status not in ["open", "in_progress", "resolved"]:
            raise HTTPException(400, "Invalid status")
        query = query.filter(Ticket.status == status)

    if priority is not None:
        if priority not in ["low", "medium", "high"]:
            raise HTTPException(400, "Invalid priority")
        query = query.filter(Ticket.priority == priority)

    return query.all()


@router.get("/{ticket_id}", response_model=TicketOut)
def ticket_detail(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if user.role == "customer" and ticket.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    if user.role == "support" and ticket.assigned_to != user.id:
        raise HTTPException(403, "Forbidden")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.owner_id == user.id).first()
    if not ticket or user.role != "customer":
        raise HTTPException(403, "Forbidden")
    if ticket.status != "open":
        raise HTTPException(400, "Only open tickets can be edited")
    ticket.title = data.title
    ticket.description = data.description
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/messages", response_model=MessageOut)
def add_message(ticket_id: int, data: MessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if user.role == "customer" and ticket.owner_id != user.id:
        raise HTTPException(403, "Forbidden")
    if user.role == "support" and ticket.assigned_to != user.id:
        raise HTTPException(403, "Forbidden")
    if ticket.status == "resolved":
        raise HTTPException(400, "Reopen ticket before replying")
    if not data.message.strip():
        raise HTTPException(422, "Message cannot be blank")
    
    msg = TicketMessage(ticket_id=ticket.id, sender_id=user.id, message=data.message.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/{ticket_id}/messages", response_model=list[MessageOut])
def list_messages(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Вызываем детальную информацию для автоматической проверки прав доступа текущего пользователя
    ticket_detail(ticket_id, db, user)
    return db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id).all()


@router.patch("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(ticket_id: int, data: AssignTicket, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admins only")
    support = db.query(User).filter(User.id == data.support_id, User.role == "support").first()
    if not support:
        raise HTTPException(400, "Assigned user must have support role")
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.assigned_to = support.id
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_status(ticket_id: int, data: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if user.role != "support" or ticket.assigned_to != user.id:
        raise HTTPException(403, "Assigned support only")
    
    # Обязательное бизнес-правило: строгая последовательность статусов open -> in_progress -> resolved
    if ticket.status == "open" and data.status == "in_progress":
        ticket.status = data.status
    elif ticket.status == "in_progress" and data.status == "resolved":
        ticket.status = data.status
    else:
        raise HTTPException(400, f"Cannot change status from '{ticket.status}' directly to '{data.status}'")
        
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/reopen", response_model=TicketOut)
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.owner_id == user.id).first()
    if not ticket or user.role != "customer":
        raise HTTPException(403, "Forbidden")
    if ticket.status != "resolved":
        raise HTTPException(400, "Only resolved tickets can be reopened")
    ticket.status = "open"
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/admin/stats/status")
def status_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admins only")

    from sqlalchemy import func
    rows = db.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    return {status: count for status, count in rows}