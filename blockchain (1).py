# blockchain.py - Enhanced blockchain implementation with better error handling

import json
import hashlib
import time
import os
from typing import List, Dict, Optional
from datetime import datetime

class Block:
    """Blockchain block with enhanced features."""
    
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.compute_hash()
        self.created_at = datetime.now().isoformat()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the block."""
        try:
            block_string = json.dumps({
                "index": self.index,
                "timestamp": self.timestamp,
                "data": self.data,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce
            }, sort_keys=True).encode()
            return hashlib.sha256(block_string).hexdigest()
        except Exception as e:
            print(f"Hash computation error: {e}")
            return "0" * 64  # Fallback hash

    def mine(self, difficulty: int = 2) -> bool:
        """Mine block with proof-of-work algorithm."""
        try:
            prefix = "0" * difficulty
            start_time = time.time()
            max_iterations = 1000000  # Prevent infinite loops
            
            iteration = 0
            while not self.hash.startswith(prefix) and iteration < max_iterations:
                self.nonce += 1
                self.hash = self.compute_hash()
                iteration += 1
            
            mining_time = time.time() - start_time
            
            if iteration >= max_iterations:
                print(f"Mining timeout after {max_iterations} iterations")
                return False
            
            print(f"Block mined in {mining_time:.2f}s with nonce {self.nonce}")
            return True
        except Exception as e:
            print(f"Mining error: {e}")
            return False

    def to_dict(self) -> Dict:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "created_at": self.created_at
        }

class SimpleBlockchain:
    """Enhanced blockchain implementation for voting system."""
    
    def __init__(self, difficulty: int = 2, chain_file: str = "data/chain.json"):
        self.difficulty = max(1, min(difficulty, 4))  # Limit difficulty for faster mining
        self.chain_file = chain_file
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(chain_file), exist_ok=True)
        
        self.load_chain()

    def create_genesis(self) -> bool:
        """Create genesis block."""
        try:
            genesis_data = {
                "genesis": True,
                "message": "Quantum-Blockchain Voting System Genesis Block",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0",
                "system": "enhanced"
            }
            
            print("Creating genesis block...")
            genesis = Block(0, time.time(), genesis_data, "0")
            
            if genesis.mine(self.difficulty):
                self.chain = [genesis]
                if self.save_chain():
                    print("✅ Genesis block created successfully")
                    return True
                else:
                    print("❌ Failed to save genesis block")
                    return False
            else:
                print("❌ Genesis block mining failed")
                return False
        except Exception as e:
            print(f"Genesis block creation error: {e}")
            return False

    def load_chain(self) -> bool:
        """Load blockchain from file with error recovery."""
        try:
            if not os.path.exists(self.chain_file):
                print("Chain file not found, creating genesis block...")
                return self.create_genesis()
            
            with open(self.chain_file, "r") as f:
                raw_data = json.load(f)
            
            if not raw_data or not isinstance(raw_data, list):
                print("Empty or invalid chain file, creating new genesis block...")
                return self.create_genesis()
            
            self.chain = []
            for i, block_data in enumerate(raw_data):
                try:
                    # Validate block data structure
                    required_fields = ["index", "timestamp", "data", "previous_hash", "hash"]
                    if not all(field in block_data for field in required_fields):
                        print(f"Block {i} missing required fields, recreating chain...")
                        return self.create_genesis()
                    
                    # Create block object
                    block = Block(
                        block_data["index"],
                        block_data["timestamp"],
                        block_data["data"],
                        block_data["previous_hash"]
                    )
                    block.nonce = block_data.get("nonce", 0)
                    block.hash = block_data["hash"]
                    block.created_at = block_data.get("created_at", datetime.now().isoformat())
                    
                    self.chain.append(block)
                    
                except (KeyError, TypeError, ValueError) as e:
                    print(f"Error loading block {i}: {e}")
                    print("Recreating chain due to corrupted block...")
                    return self.create_genesis()
            
            # Validate chain integrity
            if not self.is_valid():
                print("❌ Loaded chain is invalid, creating new genesis block...")
                return self.create_genesis()
            
            print(f"✅ Blockchain loaded with {len(self.chain)} blocks")
            return True
            
        except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
            print(f"Chain loading error: {e}")
            print("Creating new genesis block...")
            return self.create_genesis()

    def save_chain(self) -> bool:
        """Save blockchain to file with backup."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.chain_file), exist_ok=True)
            
            # Create backup of existing chain
            if os.path.exists(self.chain_file):
                backup_file = f"{self.chain_file}.backup"
                try:
                    os.rename(self.chain_file, backup_file)
                except OSError:
                    pass  # Backup failed, continue anyway
            
            # Save current chain
            raw_data = [block.to_dict() for block in self.chain]
            
            with open(self.chain_file, "w") as f:
                json.dump(raw_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Chain saving error: {e}")
            return False

    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block in the chain."""
        return self.chain[-1] if self.chain else None

    def add_block(self, data: Dict) -> Optional[Block]:
        """Add new block to the chain."""
        try:
            if not self.chain:
                print("No genesis block found, creating...")
                if not self.create_genesis():
                    return None
            
            last_block = self.get_latest_block()
            if not last_block:
                print("Cannot get latest block")
                return None
            
            # Create new block with enhanced data
            enhanced_data = {
                **data,
                "block_timestamp": datetime.now().isoformat(),
                "previous_block_hash": last_block.hash,
                "block_version": "2.0"
            }
            
            new_block = Block(
                last_block.index + 1,
                time.time(),
                enhanced_data,
                last_block.hash
            )
            
            print(f"Mining block #{new_block.index}...")
            
            # Mine the block
            if new_block.mine(self.difficulty):
                self.chain.append(new_block)
                if self.save_chain():
                    print(f"✅ Block #{new_block.index} added to blockchain")
                    return new_block
                else:
                    print("❌ Failed to save blockchain")
                    self.chain.pop()
                    return None
            else:
                print("❌ Block mining failed")
                return None
                
        except Exception as e:
            print(f"Add block error: {e}")
            return None

    def is_valid(self) -> bool:
        """Validate the entire blockchain."""
        try:
            if not self.chain:
                return False
            
            # Check genesis block - FIXED syntax error
            if self.chain[0].index != 0 or self.chain[0].previous_hash != "0":
                print("❌ Invalid genesis block")
                return False
            
            # Validate each block
            for i in range(1, len(self.chain)):
                current = self.chain[i]
                previous = self.chain[i - 1]
                
                # Check hash integrity
                if current.compute_hash() != current.hash:
                    print(f"❌ Block #{current.index} hash mismatch")
                    return False
                
                # Check chain linkage
                if current.previous_hash != previous.hash:
                    print(f"❌ Block #{current.index} chain linkage broken")
                    return False
                
                # Check sequential indexing
                if current.index != previous.index + 1:
                    print(f"❌ Block #{current.index} index error")
                    return False
                
                # Check proof of work
                if not current.hash.startswith("0" * self.difficulty):
                    print(f"❌ Block #{current.index} proof of work invalid")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Validation error: {e}")
            return False

    def get_chain_info(self) -> Dict:
        """Get comprehensive blockchain information."""
        try:
            latest_block = self.get_latest_block()
            
            return {
                "total_blocks": len(self.chain),
                "difficulty": self.difficulty,
                "is_valid": self.is_valid(),
                "latest_block_index": latest_block.index if latest_block else None,
                "latest_block_hash": latest_block.hash if latest_block else None,
                "chain_file": self.chain_file,
                "file_size": os.path.getsize(self.chain_file) if os.path.exists(self.chain_file) else 0
            }
        except Exception as e:
            print(f"Chain info error: {e}")
            return {"error": str(e)}

    def search_blocks(self, criteria: Dict) -> List[Block]:
        """Search blocks by criteria."""
        try:
            matching_blocks = []
            
            for block in self.chain:
                match = True
                for key, value in criteria.items():
                    if key not in block.data or block.data[key] != value:
                        match = False
                        break
                
                if match:
                    matching_blocks.append(block)
            
            return matching_blocks
        except Exception as e:
            print(f"Block search error: {e}")
            return []
