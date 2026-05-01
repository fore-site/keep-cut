import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
REDIS_URI = os.getenv("REDIS_URI")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ANILIST_API_URL = "https://graphql.anilist.co"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
APP_NAME = "Keep-Cut Game API"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
STALE_SESSION_TIMEOUT = int(os.getenv("STALE_SESSION_TIMEOUT", "3600"))