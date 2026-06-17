from fastapi import Depends, FastAPI
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import Base, engine
from app.database.session import get_db
from app.models.user import User
from app.routes import auth, employee, prospects

Base.metadata.create_all(bind=engine)


def ensure_user_schema():
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    default_password = hash_password("Password@123")

    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("""
                DO $$
                BEGIN
                    CREATE TYPE userrole AS ENUM ('admin', 'employee');
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
            """))

            if "employee_id" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN employee_id VARCHAR(50)"))

            if "password_hash" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))
                conn.execute(
                    text("UPDATE users SET password_hash = :password WHERE password_hash IS NULL"),
                    {"password": default_password},
                )
                conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL"))

            if "role" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN role userrole"))
                conn.execute(text("UPDATE users SET role = 'employee' WHERE role IS NULL"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL"))

            if "is_active" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.execute(text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN is_active SET NOT NULL"))

            if "name" in columns:
                conn.execute(text("UPDATE users SET name = email WHERE name IS NULL"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN name DROP NOT NULL"))

            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_employee_id
                ON users (employee_id)
                WHERE employee_id IS NOT NULL
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email
                ON users (email)
            """))


ensure_user_schema()

app = FastAPI(title="LMT API", docs_url=None)

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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


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
