# When adding new fields to Models do following steps

alembic revision --autogenerate -m "Comment"
alembic upgrade head 
alembic current  // to check

# Run Backend 
    activate venv 
     .venv\Scripts\activate    or .\.venv\Scripts\Activate.ps1   
     run app 
    .\.venv\Scripts\python.exe -m uvicorn main:app --reload 

    or 

    uvicorn main:app --reload     

 # check python exection path
 C:\Users\Hemand\AppData\Local\Programs\Python\Python313\python.exe -c "import main; print('ok')"