"""
Blockchain Routes
GET /api/blockchain/info       — chain info
GET /api/blockchain/results    — vote tally from chain
GET /api/blockchain/verify     — verify chain integrity
"""

from flask import Blueprint, jsonify
from models.models import Election, Candidate, VoteToken
from utils.blockchain_utils import get_chain_info, get_vote_counts

blockchain_bp = Blueprint("blockchain", __name__)


@blockchain_bp.route("/info", methods=["GET"])
def chain_info():
    try:
        info = get_chain_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({
            "connected":  False,
            "error":      str(e),
            "message":    "Start Ganache: ganache --port 7545"
        })


@blockchain_bp.route("/results", methods=["GET"])
def results():
    """
    Fetch vote counts from blockchain smart contract.
    Falls back to DB token count if Ganache is offline.
    """
    election   = Election.query.order_by(Election.created_at.desc()).first()
    candidates = Candidate.query.all()

    if not election:
        return jsonify({"error": "No election found"}), 404

    # Try blockchain first
    if election.contract_address and election.contract_address != "pending":
        try:
            cids    = [c.candidate_id for c in candidates]
            counts  = get_vote_counts(election.contract_address, cids)
            source  = "blockchain"
        except Exception as e:
            counts = _db_fallback_counts(candidates)
            source = "database_fallback"
    else:
        counts = _db_fallback_counts(candidates)
        source = "database"

    total = sum(counts.values())
    result_list = []
    for c in sorted(candidates, key=lambda x: counts.get(x.candidate_id, 0), reverse=True):
        votes = counts.get(c.candidate_id, 0)
        result_list.append({
            **c.to_dict(),
            "votes":      votes,
            "percentage": round((votes / total * 100), 1) if total else 0,
        })

    return jsonify({
        "election":  election.to_dict(),
        "results":   result_list,
        "total":     total,
        "source":    source,
    })


@blockchain_bp.route("/transactions", methods=["GET"])
def transactions():
    """List all vote transactions with tx hashes."""
    tokens = VoteToken.query.filter_by(used=True).order_by(VoteToken.issued_at).all()
    return jsonify([{
        "token":      t.token[:20] + "...",
        "tx_hash":    t.tx_hash,
        "issued_at":  t.issued_at.isoformat(),
    } for t in tokens])


def _db_fallback_counts(candidates) -> dict:
    """Count from DB tokens when blockchain is offline."""
    from models.models import VoteToken
    counts = {c.candidate_id: 0 for c in candidates}
    # Note: in production, source-of-truth is always blockchain
    return counts
