from sqlmodel import Session, select
from database.session import engine, init_db
from models.user import User
from auth import hash_password

def seed_database():
    init_db()
    with Session(engine) as session:
        if session.exec(select(User)).first():
            print("Database already contains records. Skipping seed.")
            return

        users = [
            User(username="admin_user", email="admin@sendit.co.ke", hashed_password=hash_password("AdminPass123!"), full_name="Admin Director", role="admin"),
            User(username="manager_nyeri", email="nyeri@sendit.co.ke", hashed_password=hash_password("ManagerPass123!"), full_name="Nyeri Logistics Manager", role="manager"),
            User(username="staff_rider", email="rider@sendit.co.ke", hashed_password=hash_password("StaffPass123!"), full_name="Courier Rider", role="staff")
        ]
        session.add_all(users)
        session.commit()
        print("Successfully seeded Admin, Manager, and Staff accounts!")

if __name__ == "__main__":
    seed_database()