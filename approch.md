A production-grade application is mostly about preventing those problems from ever occurring again.

1. Establish strict layer boundaries

The most important rule:

Routes
  ↓
Services
  ↓
Models
  ↓
Database

Never the reverse.

Good
# routes/prospects.py
from app.services.prospect_service import create_prospect
# services/prospect_service.py
from app.models.prospects import Prospect
Bad
# models/prospects.py
from app.services.prospect_service import create_prospect
# models/prospects.py
from app.routes.prospects import router
# models/prospects.py
from app.schemas import ProspectCreate

Models should never know routes, services, or schemas exist.

2. Separate responsibilities
Models

Only SQLAlchemy definitions.

class Prospect(Base):
    ...

No business logic.

No API code.

No FastAPI imports.

Schemas

Only request/response validation.

class ProspectCreate(BaseModel):
    ...
class ProspectOut(BaseModel):
    ...

No database queries.

Services

Business logic.

async def create_prospect(...):
    ...
async def calculate_payment_summary(...):
    ...

No FastAPI route decorators.

Routes

HTTP only.

@router.post("/")
async def create(...):

Should be very thin.

Ideally:

@router.post("/")
async def create(...):
    return await prospect_service.create(...)
3. Stop importing from package roots

Avoid:

from app.models import Prospect

Prefer:

from app.models.prospects import Prospect

Avoid:

from app.services import prospect_service

Prefer:

import app.services.prospect_service as prospect_service

This alone eliminates many circular imports.

4. Keep init.py minimal

Bad:

# app/services/__init__.py

from .prospect_service import *
from .payment_service import *

Good:

"""
Service package.
"""

or:

__all__ = []

Production systems often keep package initializers nearly empty.

5. Build models from database first

Before writing ORM models:

\d prospects
\d payments
\d users

Then create matching models.

Every table should map 1:1 to a model.

6. Use relationships consistently

If one side has:

prospect = relationship(
    "Prospect",
    back_populates="payments",
)

The other side must have:

payments = relationship(
    "Payment",
    back_populates="prospect",
)

Always create both sides together.

7. Use enums properly

You already have PostgreSQL enums.

Good:

class ProspectStage(str, Enum):
    new = "new"
    contacted = "contacted"
stage = Column(
    Enum(
        ProspectStage,
        name="prospectstage",
        create_type=False,
    )
)

Bad:

stage = Column(String)

when database uses an enum.

8. Never hardcode auth

Your current deps:

def get_current_user():
    return {
        "id": 1,
        "role": "admin",
    }

Good for startup.

Not for production.

Next milestone should be:

Authorization: Bearer <token>

↓

decode_token()

↓

load User from database

↓

CurrentUser
CurrentAdmin
CurrentEmployee
9. Add Alembic before more features

Right now you're manually synchronizing schema.

Install:

pip install alembic

Initialize:

alembic init migrations

Future changes become:

alembic revision --autogenerate -m "add payments table"
alembic upgrade head

Never manually edit production tables.

10. Add tests before expanding

Minimum:

tests/
├── test_auth.py
├── test_prospects.py
├── test_payments.py

Use:

pytest

Every bug you fix becomes a test.

11. Production folder structure

A structure I'd recommend for your project:

app/
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── deps.py
│
├── database/
│   ├── session.py
│   └── base.py
│
├── models/
│   ├── user.py
│   ├── prospects.py
│   ├── payments.py
│   └── ...
│
├── schemas/
│   ├── auth.py
│   ├── prospect.py
│   ├── payment.py
│   └── common.py
│
├── services/
│   ├── auth_service.py
│   ├── prospect_service.py
│   └── payment_service.py
│
├── routes/
│   ├── auth.py
│   ├── prospects.py
│   ├── payments.py
│   └── dashboard.py
│
├── utils/
│
└── main.py
12. Recommended order from here

Now that startup works:

Phase 1

Fix ORM models completely.

User
Course
Prospect
Payment
Document
Notification
RefreshToken

Ensure relationships work.

Phase 2

Implement real JWT auth.

Login
Access token
Current user
Role checking
Refresh token
Phase 3

Finish schemas.

ProspectCreate
ProspectUpdate
ProspectOut
PaymentCreate
PaymentOut
PaginatedResponse
Phase 4

Finish services.

Prospect service
Payment service
Dashboard service
Phase 5

Add Alembic migrations.

Phase 6

Add tests.