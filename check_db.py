from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import User, Referral, DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_db():
    db = SessionLocal()
    try:
        print("Users:")
        users = db.query(User).all()
        for user in users:
            print(f"ID: {user.id}, TG_ID: {user.tg_id}, Username: {user.username}, Points: {user.points}")

        print("\nReferrals:")
        referrals = db.query(Referral).all()
        for referral in referrals:
            print(
                f"ID: {referral.id}, User TG_ID: {referral.user_tg_id}, Friend TG_ID: {referral.friend_tg_id}, Points: {referral.points}")
    finally:
        db.close()


if __name__ == "__main__":
    check_db()