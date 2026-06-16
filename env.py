from dotenv import load_dotenv
import os

load_dotenv()

config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL")
)