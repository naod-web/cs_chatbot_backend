import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'SECRET_KEY_HERE')
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    PORT = int(os.getenv('PORT', 5001))
    
    # Database Configuration (USING YOUR SERVER IP)
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 1234))
    DB_NAME = os.getenv('DB_NAME', 'DB_CHATBOT')
    DB_USERNAME = os.getenv('DB_USERNAME', 'user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'paswd')
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    # Connection string matching your Spring Boot configuration
    DB_CONNECTION_STRING = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USERNAME};"
        f"PWD={DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )
    
    # Pool configuration (from HikariCP)
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 10))
    DB_MIN_IDLE = int(os.getenv('DB_MIN_IDLE', 5))
    DB_IDLE_TIMEOUT = int(os.getenv('DB_IDLE_TIMEOUT', 30000))
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET', 'JWT_SECRET_KEY_HERE')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_EXPIRATION', 3600000)) / 1000)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_EXPIRATION', 86400000)) / 1000)
    
    # Chatbot Configuration
    CHATBOT_CONFIDENCE_THRESHOLD = float(os.getenv('CHATBON_CONFIDENCE_THRESHOLD', 0.3))
    CHATBOT_MAX_HISTORY = int(os.getenv('CHATBOT_MAX_HISTORY', 50))
    CHATBOT_DEFAULT_RESPONSE = "I understand you're asking about: '{query}'. Could you please provide more details?"
    
    # CORS Configuration - Allow all for development
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'chatbot.log')





