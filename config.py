import os

MONGO_URI = "mongodb+srv://jdtiles2002_db_user:KJs2002@cluster0.aokxw8m.mongodb.net/jdtiles?retryWrites=true&w=majority"

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password123")