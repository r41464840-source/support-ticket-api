from fastapi import FastAPI

from app.database import Base, engine
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.routers.tickets import router as tickets_router
from app.routers.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Support Ticket API")

app.include_router(auth_router)
app.include_router(tickets_router)


@app.get("/")
def home():
    return {"message": "Support Ticket API is running"}
