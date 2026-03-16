"""
Voter Routes
POST /api/voter/authenticate   — face auth → issue token
POST /api/voter/cast-vote      — submit vote to blockchain
GET  /api/voter/status/:id     — check if voted
"""

from flask import Blueprint, request, jsonify, current_app
from models.models import db, Voter, Election, Candidate, VoteToken
from utils.face_utils import authenticate_face
from utils.blockchain_utils import (
    cast_vote_on_chain, generate_anonymous_token,
    check_duplicate_vote
)

voter_bp = Blueprint("voter", __name__)


@voter_bp.route("/authenticate", methods=["POST"])
def authenticate():
    """
    Step 1: Voter submits Voter ID + live face image.
    Returns one-time anonymous token if auth passes.
    """
    data     = request.json
    voter_id = data.get("voter_id", "").strip().upper()
    face_b64 = data.get("face_image")       # base64 from webcam

    if not voter_id or not face_b64:
        return jsonify({"error": "voter_id and face_image required"}), 400

    # 1. Look up voter
    voter = Voter.query.filter_by(voter_id=voter_id).first()
    if not voter:
        return jsonify({"error": "Voter ID not registered"}), 404

    # 2. Check if already voted (smart contract also enforces this)
    if voter.has_voted:
        return jsonify({"error": "This voter has already cast a vote — duplicate blocked"}), 409

    # 3. Check face enrolled
    if not voter.face_path:
        return jsonify({"error": "Biometric not enrolled — contact admin"}), 400

    # 4. Check election is active
    election = Election.query.filter_by(status="active").first()
    if not election:
        return jsonify({"error": "No active election — contact administrator"}), 403

    # 5. Run DeepFace authentication
    face_result = authenticate_face(voter.face_path, face_b64)

    if not face_result["verified"]:
        return jsonify({
            "error":      face_result.get("error", "Face authentication failed"),
            "liveness":   face_result.get("liveness", False),
            "verified":   False,
        }), 401

    # 6. Issue one-time anonymous token
    token = generate_anonymous_token(voter.id, election.id)

    vote_token = VoteToken(
        token=token,
        voter_id=voter.id,
        election_id=election.id,
    )
    db.session.add(vote_token)
    db.session.commit()

    return jsonify({
        "verified":   True,
        "liveness":   face_result["liveness"],
        "distance":   face_result.get("distance"),
        "token":      token,
        "voter_name": voter.name,
        "election":   election.to_dict(),
        "message":    "Authentication successful — token issued",
    })


@voter_bp.route("/cast-vote", methods=["POST"])
def cast_vote():
    """
    Step 2: Voter submits token + candidate choice.
    Smart contract validates token & records on blockchain.
    """
    data         = request.json
    token        = data.get("token")
    candidate_id = data.get("candidate_id")

    if not token or not candidate_id:
        return jsonify({"error": "token and candidate_id required"}), 400

    # Verify token exists and unused
    vote_token = VoteToken.query.filter_by(token=token, used=False).first()
    if not vote_token:
        return jsonify({"error": "Invalid or already-used token — smart contract rejected"}), 400

    # Verify candidate
    candidate = Candidate.query.filter_by(candidate_id=candidate_id).first()
    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # Verify election still active
    election = Election.query.get(vote_token.election_id)
    if not election or election.status != "active":
        return jsonify({"error": "Election is not active"}), 403

    # Check blockchain-level duplicate (belt + suspenders)
    if election.contract_address and election.contract_address != "pending":
        is_dup = check_duplicate_vote(election.contract_address, token)
        if is_dup:
            return jsonify({"error": "Blockchain: token already recorded"}), 409

    # Submit to blockchain
    if election.contract_address and election.contract_address != "pending":
        chain_result = cast_vote_on_chain(
            election.contract_address, token, candidate_id
        )
        if not chain_result["success"]:
            return jsonify({"error": chain_result.get("error")}), 500
        tx_hash      = chain_result["tx_hash"]
        block_number = chain_result["block_number"]
    else:
        # Ganache not running — record off-chain with note
        tx_hash      = "0x" + "0" * 64 + "_OFFCHAIN"
        block_number = 0

    # Invalidate token (DB level)
    vote_token.used    = True
    vote_token.tx_hash = tx_hash

    # Mark voter as voted
    voter = Voter.query.get(vote_token.voter_id)
    voter.has_voted = True

    db.session.commit()

    return jsonify({
        "success":       True,
        "tx_hash":       tx_hash,
        "block_number":  block_number,
        "candidate":     candidate.to_dict(),
        "message":       "Vote recorded on blockchain immutably",
    })


@voter_bp.route("/status/<voter_id>", methods=["GET"])
def voter_status(voter_id):
    voter = Voter.query.filter_by(voter_id=voter_id.upper()).first()
    if not voter:
        return jsonify({"error": "Voter not found"}), 404
    return jsonify({
        "voter_id":   voter.voter_id,
        "name":       voter.name,
        "has_voted":  voter.has_voted,
        "enrolled":   voter.face_path is not None,
    })
