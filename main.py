from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging

from database import get_db
from models import Referral

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/referrals/", response_model=ReferralResponse)
def create_referral(referral: ReferralCreate, db: Session = Depends(get_db)):
    logger.info(f"Attempting to create referral: {referral}")
    existing_referral = db.query(Referral).filter(
        Referral.user_tg_id == referral.user_tg_id,
        Referral.friend_tg_id == referral.friend_tg_id
    ).first()

    if existing_referral:
        logger.info(f"Existing referral found: {existing_referral}")
        return existing_referral

    new_referral = Referral(user_tg_id=referral.user_tg_id, friend_tg_id=referral.friend_tg_id)
    try:
        db.add(new_referral)
        db.commit()
        db.refresh(new_referral)
        logger.info(f"New referral created successfully: {new_referral}")
        return new_referral
    except Exception as e:
        logger.error(f"Error creating referral: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create referral")

@app.get("/referrals/{tg_id}", response_model=list[ReferralResponse])
def get_referrals(tg_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching referrals for tg_id: {tg_id}")
    referrals = db.query(Referral).filter(
        (Referral.user_tg_id == tg_id) | (Referral.friend_tg_id == tg_id)
    ).all()
    logger.info(f"Found {len(referrals)} referrals for tg_id: {tg_id}")
    return referrals

@app.get("/referrals/{tg_id}/points")
def get_user_points(tg_id: int, db: Session = Depends(get_db)):
    logger.info(f"Calculating points for tg_id: {tg_id}")
    referrals = db.query(Referral).filter(Referral.user_tg_id == tg_id).all()
    total_points = sum(referral.points for referral in referrals)
    logger.info(f"Total points for tg_id {tg_id}: {total_points}")
    return {"total_points": total_points}

