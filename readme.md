#When adding new fields to Models do following steps

alembic revision --autogenerate -m "Comment"
alembic upgrade head 
alembic current  // to check