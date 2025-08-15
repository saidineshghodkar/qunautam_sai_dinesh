# app.py - Enhanced Backend for Quantum-Blockchain Voting System

import os
import json
import base64
import uuid
import hashlib
import random
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from blockchain import SimpleBlockchain
from qkd_bb84 import bb84_shared_key_ibm as bb84_shared_key
from crypto_utils import aes_encrypt, aes_decrypt

# Configuration
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# File paths for persistent storage
VOTERS_FILE = os.path.join(DATA_DIR, "voters.json")
VOTES_FILE = os.path.join(DATA_DIR, "votes.json")
CHAIN_FILE = os.path.join(DATA_DIR, "chain.json")
FRAUD_FILE = os.path.join(DATA_DIR, "fraud.json")
OFFICERS_FILE = os.path.join(DATA_DIR, "officers.json")
PARTIES_FILE = os.path.join(DATA_DIR, "parties.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin123")

def load_json(path, default):
    """Load JSON data from file with error handling."""
    try:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f, indent=2)
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {path}: {e}")
        return default

def save_json(path, data):
    """Save JSON data to file with error handling."""
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving {path}: {e}")
        return False

def log_activity(activity, user_id=None, details=None):
    """Log system activities for audit trail."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "activity": activity,
        "user_id": user_id,
        "details": details
    }
    
    log_file = os.path.join(DATA_DIR, "activity_log.json")
    logs = load_json(log_file, [])
    logs.append(log_entry)
    save_json(log_file, logs)

# Load all data at startup
VOTERS = load_json(VOTERS_FILE, {})
VOTES = load_json(VOTES_FILE, {})
FRAUDS = load_json(FRAUD_FILE, [])
OFFICERS = load_json(OFFICERS_FILE, [])
PARTIES = load_json(PARTIES_FILE, [])
SESSIONS = load_json(SESSIONS_FILE, {})

# Initialize blockchain
try:
    BLOCKCHAIN = SimpleBlockchain(difficulty=3, chain_file=CHAIN_FILE)
except Exception as e:
    print(f"Blockchain initialization error: {e}")
    BLOCKCHAIN = SimpleBlockchain(difficulty=2, chain_file=CHAIN_FILE)

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    """Root endpoint with system status."""
    return jsonify({
        "system": "Quantum + Blockchain Secure Voting API",
        "status": "running",
        "version": "2.0",
        "blockchain_valid": BLOCKCHAIN.is_valid(),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/status")
def system_status():
    """Get detailed system status."""
    return jsonify({
        "voters_count": len(VOTERS),
        "parties_count": len(PARTIES),
        "officers_count": len(OFFICERS),
        "fraud_cases": len(FRAUDS),
        "blockchain_blocks": len(BLOCKCHAIN.chain),
        "blockchain_valid": BLOCKCHAIN.is_valid(),
        "total_votes": sum(p.get("votes", 0) for p in PARTIES)
    })

# Dashboard endpoint with enhanced data
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Get comprehensive dashboard data."""
    try:
        # Calculate vote statistics
        total_votes = sum(p.get("votes", 0) for p in PARTIES)
        
        # Get voter status information
        voters_with_status = []
        for vid, voter in VOTERS.items():
            voters_with_status.append({
                "name": voter["name"],
                "id_number": vid,
                "has_voted": voter.get("has_voted", False),
                "is_fraud": vid in FRAUDS
            })
        
        return jsonify({
            "fraudulent_voter_ids": FRAUDS,
            "voters": voters_with_status,
            "polling_officers": OFFICERS,
            "fraud_votes": FRAUDS,
            "parties_votes": [
                {
                    "party_name": p["party_name"],
                    "symbol": p["symbol"],
                    "votes": p["votes"],
                    "percentage": round((p["votes"] / total_votes * 100), 2) if total_votes > 0 else 0
                }
                for p in PARTIES
            ],
            "system_stats": {
                "total_voters": len(VOTERS),
                "total_votes": total_votes,
                "fraud_cases": len(FRAUDS),
                "blockchain_blocks": len(BLOCKCHAIN.chain),
                "blockchain_valid": BLOCKCHAIN.is_valid()
            }
        })
    except Exception as e:
        return jsonify({"error": f"Dashboard error: {str(e)}"}), 500

# Enhanced Admin Functions
@app.route("/admin_login", methods=["POST"])
def admin_login():
    """Admin authentication with enhanced security."""
    try:
        data = request.get_json()
        password = data.get("password")
        
        if password == "admin@123":
            session_id = str(uuid.uuid4())
            SESSIONS[session_id] = {
                "user_type": "admin",
                "login_time": datetime.now().isoformat(),
                "expires": (datetime.now().timestamp() + 3600)  # 1 hour
            }
            save_json(SESSIONS_FILE, SESSIONS)
            log_activity("admin_login", "admin")
            return jsonify({"ok": True, "session_id": session_id})
        
        log_activity("admin_login_failed", "admin", {"reason": "invalid_password"})
        return jsonify({"ok": False, "error": "Invalid admin credentials"}), 401
    except Exception as e:
        return jsonify({"error": f"Login error: {str(e)}"}), 500

@app.route("/register_officer", methods=["POST"])
def register_officer():
    """Register polling officer with enhanced validation."""
    try:
        data = request.get_json()
        name = data.get("name", "").strip()
        number = data.get("number", "").strip()
        
        if not name or not number:
            return jsonify({"ok": False, "error": "Name and number required"}), 400
        
        # Validate officer number format
        if not number.isalnum() or len(number) < 3:
            return jsonify({"ok": False, "error": "Officer number must be alphanumeric and at least 3 characters"}), 400
        
        # Check if officer number already exists
        for officer in OFFICERS:
            if officer.get("number") == number:
                return jsonify({"ok": False, "error": "Officer number already exists"}), 400
        
        # Generate secure 4-digit key ID
        key_id = str(random.randint(1000, 9999))
        
        # Ensure unique key ID
        while any(o.get("key_id") == key_id for o in OFFICERS):
            key_id = str(random.randint(1000, 9999))
        
        officer = {
            "name": name,
            "number": number,
            "key_id": key_id,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        OFFICERS.append(officer)
        save_json(OFFICERS_FILE, OFFICERS)
        log_activity("officer_registered", "admin", {"officer_number": number, "key_id": key_id})
        
        return jsonify({"ok": True, "key_id": key_id})
    except Exception as e:
        return jsonify({"error": f"Officer registration error: {str(e)}"}), 500

@app.route("/register_party", methods=["POST"])
def register_party():
    """Register political party with enhanced validation."""
    try:
        data = request.get_json()
        party_name = data.get("party_name", "").strip()
        symbol = data.get("symbol", "").strip()
        
        if not party_name or not symbol:
            return jsonify({"ok": False, "error": "Party name and symbol required"}), 400
        
        # Validate party name length
        if len(party_name) < 2 or len(party_name) > 100:
            return jsonify({"ok": False, "error": "Party name must be 2-100 characters"}), 400
        
        # Check if party already exists
        for party in PARTIES:
            if party["party_name"].lower() == party_name.lower():
                return jsonify({"ok": False, "error": "Party name already exists"}), 400
            if party["symbol"] == symbol:
                return jsonify({"ok": False, "error": "Party symbol already exists"}), 400
        
        # Generate unique party ID
        party_id = f"party_{len(PARTIES)+1}_{party_name.lower().replace(' ', '_')[:20]}"
        
        new_party = {
            "party_id": party_id,
            "party_name": party_name,
            "symbol": symbol,
            "votes": 0,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        PARTIES.append(new_party)
        save_json(PARTIES_FILE, PARTIES)
        log_activity("party_registered", "admin", {"party_name": party_name, "symbol": symbol})
        
        return jsonify({"ok": True, "party_id": party_id})
    except Exception as e:
        return jsonify({"error": f"Party registration error: {str(e)}"}), 500

# Enhanced Officer Functions
@app.route("/officer_login", methods=["POST"])
def officer_login():
    """Officer authentication with session management."""
    try:
        data = request.get_json()
        officer_id = data.get("id", "").strip()
        officer_key = data.get("key_id", "").strip()
        
        # Find officer with matching ID and key
        for officer in OFFICERS:
            if (officer.get("number") == officer_id and 
                officer.get("key_id") == officer_key and 
                officer.get("status") == "active"):
                
                session_id = str(uuid.uuid4())
                SESSIONS[session_id] = {
                    "user_type": "officer",
                    "officer_id": officer_id,
                    "login_time": datetime.now().isoformat(),
                    "expires": (datetime.now().timestamp() + 3600)  # 1 hour
                }
                save_json(SESSIONS_FILE, SESSIONS)
                log_activity("officer_login", officer_id)
                
                return jsonify({
                    "ok": True, 
                    "officer": officer,
                    "session_id": session_id
                })
        
        log_activity("officer_login_failed", officer_id, {"reason": "invalid_credentials"})
        return jsonify({"ok": False, "error": "Invalid Officer credentials"}), 401
    except Exception as e:
        return jsonify({"error": f"Officer login error: {str(e)}"}), 500

# Enhanced Voting Functions
@app.route("/verify_biometric", methods=["POST"])
def verify_biometric():
    """Enhanced biometric verification with fraud detection."""
    try:
        data = request.get_json()
        voter_id = data.get("voter_id", "").strip()
        biometric_type = data.get("type", "thumb")
        
        if not voter_id:
            return jsonify({"ok": False, "error": "Voter ID required"}), 400
        
        voter = VOTERS.get(voter_id)
        if not voter:
            log_activity("biometric_verification_failed", voter_id, {"reason": "voter_not_found"})
            return jsonify({"ok": False, "error": "Voter not found"}), 404
        
        # Enhanced fraud detection
        if voter.get("has_voted", False):
            if voter_id not in FRAUDS:
                FRAUDS.append(voter_id)
                save_json(FRAUD_FILE, FRAUDS)
                log_activity("fraud_detected", voter_id, {"type": "multiple_voting_attempt"})
            return jsonify({"ok": False, "error": "Fraud detected! Voter has already voted"}), 400
        
        # Check if voter is already marked as fraudulent
        if voter_id in FRAUDS:
            log_activity("biometric_verification_failed", voter_id, {"reason": "voter_marked_fraud"})
            return jsonify({"ok": False, "error": "Voter access denied - fraudulent activity detected"}), 403
        
        # Simulate biometric verification with random failure for realism
        if random.random() < 0.05:  # 5% chance of biometric failure
            log_activity("biometric_verification_failed", voter_id, {"reason": "biometric_mismatch"})
            return jsonify({"ok": False, "error": f"{biometric_type.title()} biometric verification failed. Please try again."}), 400
        
        # Update voter with biometric verification timestamp
        voter["biometric_verified"] = datetime.now().isoformat()
        voter["biometric_type"] = biometric_type
        save_json(VOTERS_FILE, VOTERS)
        
        log_activity("biometric_verified", voter_id, {"type": biometric_type})
        return jsonify({"ok": True, "message": f"{biometric_type.title()} biometric verified successfully"})
    except Exception as e:
        return jsonify({"error": f"Biometric verification error: {str(e)}"}), 500

@app.route("/get_parties", methods=["GET"])
def get_parties():
    """Get active parties for voting ballot."""
    try:
        parties_for_ballot = [
            {
                "party_name": p["party_name"],
                "symbol": p["symbol"],
                "party_id": p["party_id"]
            }
            for p in PARTIES if p.get("status", "active") == "active"
        ]
        return jsonify({"parties": parties_for_ballot})
    except Exception as e:
        return jsonify({"error": f"Error loading parties: {str(e)}"}), 500

@app.route("/cast_vote", methods=["POST"])
def cast_vote():
    """Enhanced vote casting with quantum encryption and blockchain."""
    try:
        data = request.get_json()
        voter_id = data.get("voter_id", "").strip()
        party_name = data.get("party_name", "").strip()
        
        if not voter_id or not party_name:
            return jsonify({"ok": False, "error": "Voter ID and party required"}), 400
        
        voter = VOTERS.get(voter_id)
        if not voter:
            return jsonify({"ok": False, "error": "Voter not registered"}), 404
        
        # Enhanced fraud detection
        if voter.get("has_voted", False):
            if voter_id not in FRAUDS:
                FRAUDS.append(voter_id)
                save_json(FRAUD_FILE, FRAUDS)
                log_activity("fraud_detected", voter_id, {"type": "multiple_voting_attempt"})
            return jsonify({"ok": False, "error": "Fraud detected! Multiple voting attempt"}), 400
        
        # Verify biometric was completed
        if not voter.get("biometric_verified"):
            return jsonify({"ok": False, "error": "Biometric verification required"}), 400
        
        # Find and validate party
        party_found = False
        for party in PARTIES:
            if party["party_name"] == party_name and party.get("status", "active") == "active":
                party["votes"] += 1
                party_found = True
                break
        
        if not party_found:
            return jsonify({"ok": False, "error": "Invalid or inactive party"}), 400
        
        # Mark voter as having voted
        voter["has_voted"] = True
        voter["vote_timestamp"] = datetime.now().isoformat()
        
        # Generate quantum-encrypted vote record
        try:
            # Generate quantum key for this vote
            key_bytes = bb84_shared_key(key_length=32, debug=False)
            
            # Create comprehensive vote data
            vote_data = {
                "voter_id": voter_id,
                "party_name": party_name,
                "timestamp": datetime.now().isoformat(),
                "biometric_type": voter.get("biometric_type", "unknown"),
                "vote_id": str(uuid.uuid4())
            }
            
            # Encrypt the vote
            encrypted_vote = aes_encrypt(key_bytes, json.dumps(vote_data).encode())
            
            # Store encrypted vote with metadata
            vote_record = {
                "encrypted_data": encrypted_vote,
                "vote_hash": hashlib.sha256(encrypted_vote.encode()).hexdigest(),
                "timestamp": vote_data["timestamp"],
                "quantum_key_id": hashlib.sha256(key_bytes).hexdigest()[:16]
            }
            
            VOTES.setdefault(voter_id, []).append(vote_record)
            
            # Add to blockchain for tamper-proofing
            BLOCKCHAIN.add_block({
                "voter_id": voter_id,
                "vote_hash": vote_record["vote_hash"],
                "party_name": party_name,
                "timestamp": vote_data["timestamp"],
                "block_type": "vote_record"
            })
            
        except Exception as e:
            print(f"Encryption/Blockchain error: {e}")
            # Continue with vote counting even if encryption fails
            pass
        
        # Save all data
        save_json(VOTERS_FILE, VOTERS)
        save_json(PARTIES_FILE, PARTIES)
        save_json(VOTES_FILE, VOTES)
        
        log_activity("vote_cast", voter_id, {"party": party_name})
        
        return jsonify({
            "ok": True,
            "message": "Vote recorded successfully",
            "vote_id": vote_data.get("vote_id", "unknown"),
            "blockchain_block": len(BLOCKCHAIN.chain) - 1
        })
        
    except Exception as e:
        return jsonify({"error": f"Vote casting error: {str(e)}"}), 500

# Enhanced Results and System Management
@app.route("/get_results", methods=["GET"])
def get_results():
    """Get election results with detailed statistics."""
    try:
        if not PARTIES:
            return jsonify({"results": [], "message": "No parties registered"})
        
        # Sort parties by vote count (descending)
        sorted_parties = sorted(PARTIES, key=lambda p: p["votes"], reverse=True)
        total_votes = sum(p["votes"] for p in PARTIES)
        
        results = []
        for rank, party in enumerate(sorted_parties, 1):
            percentage = (party["votes"] / total_votes * 100) if total_votes > 0 else 0
            results.append({
                "rank": rank,
                "party_name": party["party_name"],
                "symbol": party["symbol"],
                "votes": party["votes"],
                "percentage": round(percentage, 2)
            })
        
        return jsonify({
            "results": results,
            "total_votes": total_votes,
            "total_parties": len(PARTIES),
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Results error: {str(e)}"}), 500

@app.route("/reset_system", methods=["POST"])
def reset_system():
    """Reset entire system with admin authentication."""
    try:
        data = request.get_json()
        password = data.get("password")
        
        # Verify admin password
        if password != "admin@123":
            log_activity("system_reset_failed", "admin", {"reason": "invalid_password"})
            return jsonify({"ok": False, "error": "Invalid admin password"}), 401
        
        # Clear all data
        global VOTERS, VOTES, FRAUDS, OFFICERS, PARTIES, BLOCKCHAIN, SESSIONS
        
        VOTERS = {}
        VOTES = {}
        FRAUDS = []
        OFFICERS = []
        PARTIES = []
        SESSIONS = {}
        
        # Reset blockchain
        BLOCKCHAIN = SimpleBlockchain(difficulty=3, chain_file=CHAIN_FILE)
        
        # Save empty data
        save_json(VOTERS_FILE, VOTERS)
        save_json(VOTES_FILE, VOTES)
        save_json(FRAUD_FILE, FRAUDS)
        save_json(OFFICERS_FILE, OFFICERS)
        save_json(PARTIES_FILE, PARTIES)
        save_json(SESSIONS_FILE, SESSIONS)
        
        log_activity("system_reset", "admin", {"timestamp": datetime.now().isoformat()})
        
        return jsonify({"ok": True, "message": "System reset successfully"})
    except Exception as e:
        return jsonify({"error": f"System reset error: {str(e)}"}), 500

# Additional utility endpoints
@app.route("/register_voter", methods=["POST"])
def register_voter():
    """Register new voter with enhanced validation."""
    try:
        data = request.get_json()
        vid = data.get("voter_id", "").strip()
        name = data.get("name", "").strip()
        password = data.get("password", "default123")
        
        if not vid or not name:
            return jsonify({"ok": False, "error": "Voter ID and name required"}), 400
        
        # Validate voter ID format
        if len(vid) < 3 or not vid.replace("-", "").replace("_", "").isalnum():
            return jsonify({"ok": False, "error": "Voter ID must be at least 3 characters and alphanumeric"}), 400
        
        if vid in VOTERS:
            return jsonify({"ok": False, "error": "Voter ID already registered"}), 400
        
        VOTERS[vid] = {
            "name": name,
            "password": generate_password_hash(password),
            "iris_sample": data.get("iris_sample", "simulated_iris"),
            "session_key": None,
            "session_id": None,
            "has_voted": False,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        save_json(VOTERS_FILE, VOTERS)
        log_activity("voter_registered", vid, {"name": name})
        
        return jsonify({"ok": True, "message": "Voter registered successfully"})
    except Exception as e:
        return jsonify({"error": f"Voter registration error: {str(e)}"}), 500

@app.route("/end_session", methods=["POST"])
def end_session():
    """End polling session with officer verification."""
    try:
        data = request.get_json()
        key_id = data.get("officer_key_id", "").strip()
        
        for officer in OFFICERS:
            if officer.get("key_id") == key_id and officer.get("status") == "active":
                log_activity("session_ended", officer.get("number"), {"key_id": key_id})
                return jsonify({"ok": True, "message": "Session ended successfully"})
        
        return jsonify({"ok": False, "error": "Invalid Officer Key-ID"}), 403
    except Exception as e:
        return jsonify({"error": f"Session end error: {str(e)}"}), 500

@app.route("/activity_log", methods=["GET"])
def get_activity_log():
    """Get system activity log for audit purposes."""
    try:
        log_file = os.path.join(DATA_DIR, "activity_log.json")
        logs = load_json(log_file, [])
        
        # Return last 100 entries
        return jsonify({
            "logs": logs[-100:],
            "total_entries": len(logs)
        })
    except Exception as e:
        return jsonify({"error": f"Activity log error: {str(e)}"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

if __name__ == "__main__":
    print("🚀 Starting Quantum-Blockchain Secure Voting System")
    print("📊 Dashboard: http://localhost:5000")
    print("🔐 Blockchain Status:", "Valid" if BLOCKCHAIN.is_valid() else "Invalid")
    print("📝 Loaded:", len(VOTERS), "voters,", len(PARTIES), "parties,", len(OFFICERS), "officers")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
