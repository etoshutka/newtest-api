from typing import List
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, index=True)
    username = Column(String)
    points = Column(Integer, default=0)
    referrer_id = Column(String, ForeignKey("users.tg_id"), nullable=True)
    referrals = relationship("User", backref="referrer", remote_side=[tg_id])


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models for request/response
class UserCreate(BaseModel):
    tg_id: str
    username: str
    referrer_id: str = None


class UserResponse(BaseModel):
    tg_id: str
    username: str
    points: int
    referrals: List[str]


class ReferralResponse(BaseModel):
    referrer: UserResponse
    referrals: List[UserResponse]


app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://etoshutka.github.io/newtest-tma/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to get or create user
def get_or_create_user(db: Session, tg_id: str, username: str, referrer_id: str = None):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        user = User(tg_id=tg_id, username=username, referrer_id=referrer_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# API routes
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.tg_id == user.tg_id).first()
    if existing_user:
        return existing_user

    new_user = get_or_create_user(db, user.tg_id, user.username, user.referrer_id)

    if user.referrer_id:
        referrer = db.query(User).filter(User.tg_id == user.referrer_id).first()
        if referrer:
            referrer.points += 100  # Add points to the referrer
            db.commit()

    return new_user


@app.get("/users/{tg_id}", response_model=UserResponse)
def get_user(tg_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{tg_id}/referrals", response_model=ReferralResponse)
def get_user_referrals(tg_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    referrals = db.query(User).filter(User.referrer_id == user.tg_id).all()
    return {
        "referrer": user,
        "referrals": referrals
    }


@app.get("/")
def read_root():
    return {"message": "Welcome to the Telegram Mini App Referral System API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)