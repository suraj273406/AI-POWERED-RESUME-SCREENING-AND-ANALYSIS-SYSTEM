import os

class Config:

    SECRET_KEY = "resume-screening-secret-key"

    MYSQL_HOST = "127.0.0.1"
    MYSQL_USER = "root"

    MYSQL_PASSWORD = "PASSWORD"

    MYSQL_DATABASE = "resume_analyzer"

    UPLOAD_FOLDER = "uploads"

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024