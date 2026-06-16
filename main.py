from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.database.session import get_db
from app.models.user import User
from app.routes import auth, employee, prospects

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LMT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employee.router, prefix="/employees")
app.include_router(prospects.router, prefix="/prospects")


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    version = db.execute(text("SELECT version()")).scalar()
    user_count = db.query(User).count()

    return {
        "connected": True,
        "version": version,
        "user_count": user_count,
    }


@app.put("/masters/targets/{employee_id}")
def set_employee_target(employee_id: str, body: dict):
    return {
        "employeeId": employee_id,
        "target": body.get("target"),
        "message": "Target saved",
    }
