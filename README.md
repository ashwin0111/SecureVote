# SecureVote — Full Stack E-Voting System
## B.Tech Final Year Project

**Stack:** Python Flask + DeepFace + Web3.py + Ganache + React

---

## Project Structure

```
securevote/
├── backend/                    ← Flask Python API
│   ├── app.py                  ← App factory + CORS
│   ├── config.py               ← All settings
│   ├── requirements.txt
│   ├── models/
│   │   └── models.py           ← SQLAlchemy DB models
│   ├── routes/
│   │   ├── auth_routes.py      ← Admin login + JWT
│   │   ├── admin_routes.py     ← Voter/candidate/election management
│   │   ├── voter_routes.py     ← Face auth + vote casting
│   │   └── blockchain_routes.py← Chain info + results
│   ├── utils/
│   │   ├── face_utils.py       ← DeepFace enrollment + verification
│   │   └── blockchain_utils.py ← Web3.py + Ganache + token generation
│   └── uploads/faces/          ← Off-chain biometric storage
│
├── frontend/                   ← React app
│   └── src/
│       ├── api.js              ← All API calls
│       └── components/
│           └── FaceCapture.jsx ← Webcam capture component
│
├── contracts/
│   └── VotingContract.sol      ← Solidity smart contract
│
├── scripts/
│   └── deploy.js               ← Hardhat deploy script
│
└── hardhat.config.js           ← Hardhat + Ganache config
```

---

## Setup (Step by Step)

### STEP 1 — Install Ganache (Local Blockchain, Zero Gas)

```bash
# Install Ganache globally
npm install -g ganache

# Start Ganache on port 7545
ganache --port 7545 --chainId 1337 --accounts 10 --deterministic

# You will see:
# Available Accounts: (10 pre-funded with 1000 ETH each — FREE)
# ════════════════
# (0) 0xAbCd...   (1000 ETH)
# (1) 0x1234...   (1000 ETH)
# ...
# RPC Listening on 127.0.0.1:7545
```

> **Why Ganache?** It's a local Ethereum node that mines for free instantly.
> No real money involved. Perfect for development and project demos.

---

### STEP 2 — Compile & Deploy Smart Contract

```bash
# In project root
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox

# Compile VotingContract.sol
npx hardhat compile

# Deploy to Ganache (Ganache must be running from Step 1)
npx hardhat run scripts/deploy.js --network ganache

# Output:
# ✅ VotingContract deployed at: 0xABC123...
# 📄 Contract address saved to: backend/contract_address.json
```

---

### STEP 3 — Python Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# DeepFace will auto-download VGG-Face model weights on first run (~500 MB)
# This is a one-time download

# Run Flask server
python app.py

# Server starts at: http://localhost:5000
```

---

### STEP 4 — React Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev       # or: npm start

# Frontend at: http://localhost:3000
```

---

### STEP 5 — First Time Setup

```bash
# Create admin account (only needed once)
curl -X POST http://localhost:5000/api/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Create election
curl -X POST http://localhost:5000/api/admin/election/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "General Election 2025", "description": "National vote"}'
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/setup` | Create first admin |
| POST | `/api/auth/login` | Admin login → JWT |
| GET | `/api/auth/me` | Get current admin |

### Admin (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/voters/register` | Register voter + enroll face |
| GET | `/api/admin/voters` | List all voters |
| POST | `/api/admin/candidates` | Add candidate |
| GET | `/api/admin/candidates` | List candidates |
| POST | `/api/admin/election/create` | Create election |
| POST | `/api/admin/election/start` | Deploy contract + start |
| POST | `/api/admin/election/end` | End election |
| GET | `/api/admin/stats` | Dashboard stats |

### Voter
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voter/authenticate` | Face auth → issue token |
| POST | `/api/voter/cast-vote` | Submit vote to blockchain |
| GET | `/api/voter/status/:id` | Check if voter has voted |

### Blockchain
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/blockchain/info` | Chain info + block number |
| GET | `/api/blockchain/results` | Vote tally from smart contract |
| GET | `/api/blockchain/transactions` | All tx hashes |

---

## How It Works (Your Report Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                      VOTER FLOW                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Webcam → React → base64 image to Flask                      │
│                                                                  │
│  2. Flask → face_utils.py:                                       │
│     a) OpenCV detects face region                               │
│     b) Liveness check (blur, color variance, entropy)           │
│     c) DeepFace VGG-Face extracts 512-D feature vector         │
│     d) Cosine distance vs stored hash in SQLite (off-chain)     │
│     e) If distance < 0.40 → VERIFIED                           │
│                                                                  │
│  3. Smart contract issues one-time anonymous token              │
│     Token → SHA-256 → stored, not voter name                   │
│                                                                  │
│  4. Voter selects candidate → Flask → Web3.py → Ganache        │
│     castVote(keccak256(token), candidateId)                     │
│     Smart contract checks: hasVoted[tokenHash] == false         │
│     If used → REVERT (duplicate blocked)                        │
│                                                                  │
│  5. Vote stored in blockchain block                             │
│     Immutable. Hash-linked. Tamper-evident.                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Environment Variables (.env)

```bash
# backend/.env
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
DATABASE_URL=sqlite:///securevote.db
WEB3_PROVIDER_URI=http://127.0.0.1:7545

# DeepFace settings
DEEPFACE_MODEL=VGG-Face          # or: Facenet, ArcFace
DEEPFACE_DETECTOR=opencv         # or: retinaface (more accurate)
FACE_THRESHOLD=0.40              # lower = stricter
```

---

## Technology Mapping to Project Report

| Report Component | Implementation |
|-----------------|----------------|
| CNN Face Auth | DeepFace (VGG-Face model) |
| Liveness Detection | OpenCV Laplacian + histogram entropy |
| Feature Extraction | 512-D embedding → cosine distance |
| Off-chain Biometric | SQLite + SHA-256 hash |
| Smart Contract | VotingContract.sol (Solidity 0.8.19) |
| Blockchain | Ganache local node (free) |
| Anonymous Token | SHA-256(voter_uuid + election + salt) |
| Duplicate Prevention | `hasVoted[tokenHash]` mapping in contract |
| Vote Tally | `getVoteCount()` view function (free) |
| FAR/FRR Tuning | `FACE_THRESHOLD` in config.py |

---

## Running for Demo / Viva

```bash
# Terminal 1 — Blockchain
ganache --port 7545 --deterministic

# Terminal 2 — Deploy contract
npx hardhat run scripts/deploy.js --network ganache

# Terminal 3 — Backend
cd backend && python app.py

# Terminal 4 — Frontend
cd frontend && npm start
```

Open: `http://localhost:3000`

---

## Common Issues

**DeepFace slow on first run?**
It downloads VGG-Face weights (~500 MB) once. Subsequent runs are fast.

**"Cannot connect to blockchain"?**
Start Ganache first: `ganache --port 7545`

**Face not detected?**
- Ensure good lighting
- Face must be within OpenCV detection size (>80×80px)
- Try `DEEPFACE_DETECTOR=retinaface` for better accuracy

**"Token already used"?**
Correct! The smart contract is preventing duplicate votes.

---

## Performance Metrics (for Results chapter)

| Metric | Target | How to test |
|--------|--------|-------------|
| FAR | < 1% | Test with wrong person's face |
| FRR | < 5% | Test 20 genuine attempts |
| Face auth time | < 3s | Python `time.time()` around DeepFace.verify() |
| Blockchain TX time | < 2s | Ganache mines instantly |
| Duplicate prevention | 100% | Try voting twice with same voter ID |
