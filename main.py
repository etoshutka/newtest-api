from typing import List
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
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

# Database models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, index=True)
    username = Column(String)
    ref_link = Column(String, unique=True)
    points = Column(Integer, default=0)

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    user_tg_id = Column(String, ForeignKey("users.tg_id"))
    friend_tg_id = Column(String, ForeignKey("users.tg_id"))
    points = Column(Integer, default=0)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for request/response
class UserCreate(BaseModel):
    tg_id: str
    username: str

class UserResponse(BaseModel):
    tg_id: str
    username: str
    ref_link: str
    points: int

class ReferralCreate(BaseModel):
    user_tg_id: str
    friend_tg_id: str

class ReferralResponse(BaseModel):
    date: datetime
    user_tg_id: str
    friend_tg_id: str
    points: int

class UpdatePoints(BaseModel):
    points: int

class ReferralLinkUpdate(BaseModel):
    ref_link: str

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене замените на конкретные домены
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
def get_or_create_user(db: Session, tg_id: str, username: str):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        ref_link = f"https://t.me/tma123_bot?startapp={tg_id}"
        user = User(tg_id=tg_id, username=username, ref_link=ref_link, points=0)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Received {request.method} request to {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    print(f"Responded with status {response.status_code}")
    return response

# API routes
@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return get_or_create_user(db, user.tg_id, user.username)

@app.get("/users/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/users/{tg_id}", response_model=UserResponse)
def get_user(tg_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/{tg_id}/friends", response_model=List[UserResponse])
def get_user_friends(tg_id: str, db: Session = Depends(get_db)):
    referrals = db.query(Referral).filter(Referral.user_tg_id == tg_id).all()
    friend_ids = [referral.friend_tg_id for referral in referrals]
    friends = db.query(User).filter(User.tg_id.in_(friend_ids)).all()
    return friends

@app.post("/referrals/", response_model=ReferralResponse)
def create_referral(referral: ReferralCreate, db: Session = Depends(get_db)):
    existing_referral = db.query(Referral).filter(
        Referral.user_tg_id == referral.user_tg_id,
        Referral.friend_tg_id == referral.friend_tg_id
    ).first()

    if existing_referral:
        raise HTTPException(status_code=400, detail="Referral already exists")

    new_referral = Referral(
        user_tg_id=referral.user_tg_id,
        friend_tg_id=referral.friend_tg_id,
        points=100  # You can adjust the points as needed
    )
    db.add(new_referral)

    # Update user's points
    user = db.query(User).filter(User.tg_id == referral.user_tg_id).first()
    if user:
        user.points += 100  # Increase user's points

    db.commit()
    db.refresh(new_referral)
    return new_referral

@app.get("/users/{tg_id}/referral_link")
def get_referral_link(tg_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"referral_link": user.ref_link}

@app.post("/users/{tg_id}/referral_link")
def update_referral_link(tg_id: str, link_data: ReferralLinkUpdate, db: Session = Depends(get_db)):
    user = get_or_create_user(db, tg_id, "")  # Create user if not exists
    user.ref_link = link_data.ref_link
    db.commit()
    return {"message": "Referral link updated successfully"}

@app.get("/users/{tg_id}/points")
def get_user_points(tg_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"points": user.points}

@app.post("/users/{tg_id}/points")
def update_user_points(tg_id: str, update: UpdatePoints, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.points = update.points
    db.commit()
    db.refresh(user)
    return {"points": user.points}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Referral System API"}

