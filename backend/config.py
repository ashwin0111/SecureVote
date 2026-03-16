import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "securevote-secret-2025")

    # SQLite — swap for PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///securevote.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Face uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads", "faces")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024   # 10 MB

    # Blockchain — Ganache local node (free, zero gas)
    WEB3_PROVIDER_URI = os.environ.get("WEB3_PROVIDER_URI", "http://127.0.0.1:7545")

    # DeepFace settings
    DEEPFACE_MODEL    = "VGG-Face"          # Best accuracy; alternatives: Facenet, ArcFace
    DEEPFACE_DETECTOR = "opencv"            # Fast; alternatives: retinaface, mtcnn
    FACE_THRESHOLD    = 0.40               # Cosine distance — lower = stricter

    # JWT
    JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-securevote-2025")
    JWT_EXP_HOURS = 2
