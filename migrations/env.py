import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:Happen123!@localhost:5432/livestockdb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
