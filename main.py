from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
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

# Database model
class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(Integer, index=True)
    friend_tg_id = Column(Integer, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    points = Column(Integer, default=100)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for request/response
class ReferralCreate(BaseModel):
    user_tg_id: int
    friend_tg_id: int

class ReferralResponse(BaseModel):
    id: int
    user_tg_id: int
    friend_tg_id: int
    date: datetime
    points: int

    class Config:
        orm_mode = True

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://etoshutka.github.io/newtest-tma"],
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

@app.post("/referrals/", response_model=ReferralResponse)
def create_referral(referral: ReferralCreate, db: Session = Depends(get_db)):
    existing_referral = db.query(Referral).filter(
        Referral.user_tg_id == referral.user_tg_id,
        Referral.friend_tg_id == referral.friend_tg_id
    ).first()

    if existing_referral:
        return existing_referral

    new_referral = Referral(user_tg_id=referral.user_tg_id, friend_tg_id=referral.friend_tg_id)
    db.add(new_referral)
    db.commit()
    db.refresh(new_referral)

    return new_referral

@app.get("/referrals/{tg_id}", response_model=List[ReferralResponse])
def get_referrals(tg_id: int, db: Session = Depends(get_db)):
    referrals = db.query(Referral).filter(
        (Referral.user_tg_id == tg_id) | (Referral.friend_tg_id == tg_id)
    ).all()
    return referrals

@app.get("/referrals/{tg_id}/points")
def get_user_points(tg_id: int, db: Session = Depends(get_db)):
    referrals = db.query(Referral).filter(Referral.user_tg_id == tg_id).all()
    total_points = sum(referral.points for referral in referrals)
    return {"total_points": total_points}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)