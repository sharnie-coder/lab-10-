from sqlmodel import Session, select

from auth import hash_password
from database.session import engine
from models.user import User


def seed():

    with Session(engine) as session:

        admin = session.exec(
            select(User).where(User.username == "admin")
        ).first()

        if admin:
            print("Admin already exists.")
            return

        admin = User(
            username="admin",
            email="admin@sendit.com",
            hashed_password=hash_password("Admin123!"),
            full_name="System Administrator",
            role="admin"
        )

        session.add(admin)
        session.commit()

        print("Admin created.")


if __name__ == "__main__":
    seed()