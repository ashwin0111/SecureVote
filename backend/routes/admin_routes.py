"""
Admin Routes (JWT protected)
POST /api/admin/voters/register    — register voter + enroll face
GET  /api/admin/voters             — list all voters
POST /api/admin/candidates         — add candidate
GET  /api/admin/candidates         — list candidates
POST /api/admin/election/start     — start election (deploy contract)
POST /api/admin/election/end       — end election
GET  /api/admin/election           — get current election
"""

from flask import Blueprint, request, jsonify, current_app
from models.models import db, Voter, Candidate, Election
from utils.face_utils import enroll_face
from utils.blockchain_utils import deploy_voting_contract
from routes.auth_routes import require_admin

admin_bp = Blueprint("admin", __name__)


# ── VOTER REGISTRATION ────────────────────────────────────────────────────────

@admin_bp.route("/voters/register", methods=["POST"])
@require_admin
def register_voter():
    """Register voter with biometric face enrollment."""
    data     = request.json
    voter_id = data.get("voter_id", "").strip().upper()
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    dob      = data.get("dob", "")
    face_b64 = data.get("face_image")        # Base64 from admin webcam

    if not all([voter_id, name, email, face_b64]):
        return jsonify({"error": "voter_id, name, email, face_image are required"}), 400

    if Voter.query.filter_by(voter_id=voter_id).first():
        return jsonify({"error": f"Voter ID {voter_id} already registered"}), 409

    if Voter.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Run face enrollment (DeepFace)
    face_result = enroll_face(voter_id, face_b64)
    if not face_result["success"]:
        return jsonify({"error": face_result.get("error", "Face enrollment failed")}), 400

    voter = Voter(
        voter_id=voter_id,
        name=name,
        email=email,
        dob=dob,
        face_path=face_result["face_path"],
        face_hash=face_result["face_hash"],
        registered_by=request.admin.id,
    )
    db.session.add(voter)
    db.session.commit()

    return jsonify({
        "message":   f"Voter {name} registered with biometric enrollment",
        "voter":     voter.to_dict(),
        "face_hash": face_result["face_hash"][:16] + "...",
    }), 201


@admin_bp.route("/voters", methods=["GET"])
@require_admin
def list_voters():
    voters = Voter.query.order_by(Voter.created_at.desc()).all()
    return jsonify([v.to_dict() for v in voters])


# ── CANDIDATES ────────────────────────────────────────────────────────────────

@admin_bp.route("/candidates", methods=["POST"])
@require_admin
def add_candidate():
    data = request.json
    cid  = data.get("candidate_id", "").strip().upper()
    name = data.get("name", "").strip()
    party = data.get("party", "")
    symbol = data.get("symbol", "🔵")

    if not cid or not name:
        return jsonify({"error": "candidate_id and name required"}), 400
    if Candidate.query.filter_by(candidate_id=cid).first():
        return jsonify({"error": "Candidate ID already exists"}), 409

    c = Candidate(candidate_id=cid, name=name, party=party, symbol=symbol)
    db.session.add(c)
    db.session.commit()
    return jsonify({"message": "Candidate added", "candidate": c.to_dict()}), 201


@admin_bp.route("/candidates", methods=["GET"])
def list_candidates():
    """Public — voters need this."""
    candidates = Candidate.query.all()
    return jsonify([c.to_dict() for c in candidates])


# ── ELECTION CONTROL ──────────────────────────────────────────────────────────

@admin_bp.route("/election", methods=["GET"])
def get_election():
    election = Election.query.order_by(Election.created_at.desc()).first()
    if not election:
        return jsonify({"election": None})
    return jsonify({"election": election.to_dict()})


@admin_bp.route("/election/create", methods=["POST"])
@require_admin
def create_election():
    if Election.query.filter_by(status="active").first():
        return jsonify({"error": "An election is already active"}), 400
    data = request.json
    election = Election(
        title=data.get("title", "General Election 2025"),
        description=data.get("description", ""),
        status="pending",
        contract_address="pending"
    )
    db.session.add(election)
    db.session.commit()
    return jsonify({"message": "Election created", "election": election.to_dict()}), 201


@admin_bp.route("/election/start", methods=["POST"])
@require_admin
def start_election():
    """
    Deploy smart contract to Ganache and activate election.
    Ganache mines instantly — zero cost.
    """
    election = Election.query.filter_by(status="pending").first()
    if not election:
        return jsonify({"error": "No pending election — create one first"}), 400

    candidates = Candidate.query.all()
    if len(candidates) < 2:
        return jsonify({"error": "Add at least 2 candidates before starting"}), 400

    # Deploy contract to Ganache
    try:
        cids   = [c.candidate_id for c in candidates]
        cnames = [c.name for c in candidates]
        contract_address = deploy_voting_contract(cids, cnames)
    except Exception as e:
        # Ganache not running — mark as pending with note
        contract_address = "pending"
        import logging
        logging.getLogger(__name__).warning(f"Blockchain deploy failed: {e}")

    import datetime
    election.status           = "active"
    election.contract_address = contract_address
    election.start_time       = datetime.datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message":          "Election started",
        "contract_address": contract_address,
        "election":         election.to_dict(),
    })


@admin_bp.route("/election/end", methods=["POST"])
@require_admin
def end_election():
    import datetime
    election = Election.query.filter_by(status="active").first()
    if not election:
        return jsonify({"error": "No active election"}), 400
    election.status   = "ended"
    election.end_time = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Election ended", "election": election.to_dict()})


# ── DASHBOARD STATS ───────────────────────────────────────────────────────────

@admin_bp.route("/stats", methods=["GET"])
@require_admin
def stats():
    from models.models import VoteToken
    total_voters = Voter.query.count()
    voted        = Voter.query.filter_by(has_voted=True).count()
    candidates   = Candidate.query.count()
    tokens_used  = VoteToken.query.filter_by(used=True).count()
    election     = Election.query.order_by(Election.created_at.desc()).first()

    return jsonify({
        "total_voters": total_voters,
        "voted":        voted,
        "not_voted":    total_voters - voted,
        "candidates":   candidates,
        "votes_cast":   tokens_used,
        "election":     election.to_dict() if election else None,
    })
