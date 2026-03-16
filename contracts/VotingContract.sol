// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title VotingContract
 * @notice SecureVote — Blockchain E-Voting Smart Contract
 *
 * Key design decisions (from project report):
 *  - Votes stored as keccak256(token) → anonymity preserved
 *  - One token → one vote enforced at contract level
 *  - Election window enforced by isActive flag
 *  - No admin can alter cast votes (immutable mapping)
 *  - Vote counts readable by anyone (transparency)
 *
 * Deploy on: Ganache local (free) or Ethereum Sepolia testnet
 */

contract VotingContract {

    // ── State ─────────────────────────────────────────────────────────────

    address public owner;
    bool    public isActive;

    struct Candidate {
        bytes32 id;
        string  name;
        uint256 voteCount;
        bool    exists;
    }

    mapping(bytes32 => Candidate) public candidates;    // candidateId → Candidate
    mapping(bytes32 => bool)      public hasVoted;      // tokenHash   → voted?
    bytes32[]                     public candidateIds;

    // ── Events ────────────────────────────────────────────────────────────

    event ElectionStarted(uint256 timestamp);
    event ElectionEnded(uint256 timestamp, uint256 totalVotes);

    /// @notice Emitted on every vote. tokenHash is anonymous — not linked to voter.
    event VoteCast(
        bytes32 indexed tokenHash,
        bytes32 indexed candidateId,
        uint256 timestamp
    );

    // ── Modifiers ─────────────────────────────────────────────────────────

    modifier onlyOwner()  { require(msg.sender == owner,  "Not owner");   _; }
    modifier electionOn() { require(isActive, "Election not active");      _; }
    modifier electionOff(){ require(!isActive, "Election already active"); _; }

    // ── Constructor ───────────────────────────────────────────────────────

    /**
     * @param _candidateIds   bytes32[] — candidate identifiers (e.g. "C001")
     * @param _candidateNames string[]  — display names
     */
    constructor(
        bytes32[] memory _candidateIds,
        string[]  memory _candidateNames
    ) {
        require(_candidateIds.length == _candidateNames.length, "Length mismatch");
        require(_candidateIds.length >= 2, "Need at least 2 candidates");

        owner = msg.sender;

        for (uint i = 0; i < _candidateIds.length; i++) {
            bytes32 cid = _candidateIds[i];
            require(!candidates[cid].exists, "Duplicate candidate ID");
            candidates[cid] = Candidate({
                id:        cid,
                name:      _candidateNames[i],
                voteCount: 0,
                exists:    true
            });
            candidateIds.push(cid);
        }
    }

    // ── Admin Functions ───────────────────────────────────────────────────

    function startElection() external onlyOwner electionOff {
        isActive = true;
        emit ElectionStarted(block.timestamp);
    }

    function endElection() external onlyOwner electionOn {
        isActive = false;
        emit ElectionEnded(block.timestamp, getTotalVotes());
    }

    // ── Core Voting ───────────────────────────────────────────────────────

    /**
     * @notice Cast a vote.
     * @param tokenHash   keccak256 of one-time token — preserves anonymity
     * @param candidateId bytes32 candidate identifier
     *
     * Smart contract enforces:
     *  1. Election must be active
     *  2. Token must not have been used before (no duplicates)
     *  3. Candidate must exist
     */
    function castVote(
        bytes32 tokenHash,
        bytes32 candidateId
    ) external electionOn {
        // Anti-duplicate: revert if token already used
        require(!hasVoted[tokenHash], "Token already used - duplicate vote rejected");

        // Candidate must exist
        require(candidates[candidateId].exists, "Candidate does not exist");

        // Mark token as used (nullifier)
        hasVoted[tokenHash] = true;

        // Increment vote count
        candidates[candidateId].voteCount += 1;

        emit VoteCast(tokenHash, candidateId, block.timestamp);
    }

    // ── View Functions (free to call) ─────────────────────────────────────

    function getVoteCount(bytes32 candidateId) external view returns (uint256) {
        return candidates[candidateId].voteCount;
    }

    function getTotalVotes() public view returns (uint256) {
        uint256 total = 0;
        for (uint i = 0; i < candidateIds.length; i++) {
            total += candidates[candidateIds[i]].voteCount;
        }
        return total;
    }

    function getCandidateCount() external view returns (uint256) {
        return candidateIds.length;
    }

    function getAllResults() external view returns (
        bytes32[] memory ids,
        string[]  memory names,
        uint256[] memory counts
    ) {
        uint256 n = candidateIds.length;
        ids    = new bytes32[](n);
        names  = new string[](n);
        counts = new uint256[](n);
        for (uint i = 0; i < n; i++) {
            bytes32 cid = candidateIds[i];
            ids[i]    = cid;
            names[i]  = candidates[cid].name;
            counts[i] = candidates[cid].voteCount;
        }
    }
}
