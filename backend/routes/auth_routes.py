"""
Auth Routes — Admin login, JWT issuance
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models.models import db, Admin
import jwt
import datetime

auth_bp = Blueprint("auth", __name__)


def _make_token(admin_id: str) -> str:
    secret = current_app.config["JWT_SECRET"]
    exp    = datetime.datetime.utcnow() + datetime.timedelta(
                 hours=current_app.config["JWT_EXP_HOURS"])
    return jwt.encode({"sub": admin_id, "exp": exp}, secret, algorithm="HS256")


def require_admin(f):
    """Decorator: verify JWT from Authorization header."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET"],
                                 algorithms=["HS256"])
            admin = Admin.query.get(payload["sub"])
            if not admin:
                return jsonify({"error": "Admin not found"}), 401
            request.admin = admin
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/setup", methods=["POST"])
def setup_admin():
    """Create first admin account (only if none exists)."""
    if Admin.query.count() > 0:
        return jsonify({"error": "Admin already exists"}), 400
    data = request.json
    admin = Admin(
        username=data["username"],
        password_hash=generate_password_hash(data["password"])
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"message": "Admin created", "token": _make_token(admin.id)})


@auth_bp.route("/login", methods=["POST"])
def login():
    data  = request.json
    admin = Admin.query.filter_by(username=data.get("username")).first()
    if not admin or not check_password_hash(admin.password_hash, data.get("password", "")):
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({
        "token": _make_token(admin.id),
        "admin": admin.to_dict()
    })


@auth_bp.route("/me", methods=["GET"])
@require_admin
def me():
    return jsonify(request.admin.to_dict())
