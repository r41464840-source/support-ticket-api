
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "Sizning_Maxfiy_Kalitingiz_2026"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(user_id: int):
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expires},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    username = data.username.strip()
    email = str(data.email).strip().lower()

    if not username:
        raise HTTPException(422, "Username cannot be blank")

    if db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first():
        raise HTTPException(409, "Username or email already exists")

    user = User(
        username=username,
        email=email,
        hashed_password=password_hash.hash(data.password),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
def login(
    username: str = __import__("fastapi").Form(),
    password: str = __import__("fastapi").Form(),
    db: Session = Depends(get_db),
):
    email = username.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not password_hash.verify(
        password, user.hashed_password
    ):
        raise HTTPException(401, "Incorrect email or password")

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "User not found")

    return user
