from extensions import db
from datetime import datetime
import uuid

class Voter(db.Model):
    __tablename__ = "voters"
    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    voter_id    = db.Column(db.String(50), unique=True, nullable=False)
    name        = db.Column(db.String(120), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    dob         = db.Column(db.String(20))
    face_path   = db.Column(db.String(260))
    face_hash   = db.Column(db.String(64))
    has_voted   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    registered_by = db.Column(db.String(36))
    def to_dict(self):
        return {"id": self.id, "voter_id": self.voter_id, "name": self.name,
                "email": self.email, "has_voted": self.has_voted,
                "face_enrolled": self.face_path is not None,
                "created_at": self.created_at.isoformat()}

class Admin(db.Model):
    __tablename__ = "admins"
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {"id": self.id, "username": self.username}

class Candidate(db.Model):
    __tablename__ = "candidates"
    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = db.Column(db.String(20), unique=True, nullable=False)
    name         = db.Column(db.String(120), nullable=False)
    party        = db.Column(db.String(120))
    symbol       = db.Column(db.String(10), default="🔵")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {"id": self.id, "candidate_id": self.candidate_id,
                "name": self.name, "party": self.party, "symbol": self.symbol}

class Election(db.Model):
    __tablename__ = "elections"
    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title            = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text)
    status           = db.Column(db.String(20), default="pending")
    start_time       = db.Column(db.DateTime)
    end_time         = db.Column(db.DateTime)
    contract_address = db.Column(db.String(42))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {"id": self.id, "title": self.title, "description": self.description,
                "status": self.status, "contract_address": self.contract_address,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None}

class VoteToken(db.Model):
    __tablename__ = "vote_tokens"
    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token       = db.Column(db.String(100), unique=True, nullable=False)
    voter_id    = db.Column(db.String(36), db.ForeignKey("voters.id"))
    election_id = db.Column(db.String(36), db.ForeignKey("elections.id"))
    used        = db.Column(db.Boolean, default=False)
    tx_hash     = db.Column(db.String(66))
    issued_at   = db.Column(db.DateTime, default=datetime.utcnow)
