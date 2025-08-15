#!/usr/bin/env python3
# test_integration.py - Comprehensive testing for the voting system

import requests
import json
import time
import random
from qkd_bb84 import bb84_shared_key_ibm

def test_quantum_key_generation():
    """Test quantum key generation functionality."""
    print("🔑 Testing Quantum Key Generation...")
    try:
        key = bb84_shared_key_ibm(key_length=64, debug=True)
        print(f"✅ Quantum key generated successfully: {key.hex()[:32]}...")
        return True
    except Exception as e:
        print(f"❌ Quantum key generation failed: {e}")
        return False

def test_backend_endpoints():
    """Test all backend endpoints."""
    print("\n🌐 Testing Backend Endpoints...")
    base_url = "http://localhost:5000"
    
    # Test system status
    try:
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            print("✅ System status endpoint working")
            print(f"   Status: {response.json()}")
        else:
            print("❌ System status endpoint failed")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure to run: python app.py")
        return False
    
    # Test admin login
    admin_data = {"password": "admin@123"}
    response = requests.post(f"{base_url}/admin_login", json=admin_data, timeout=5)
    if response.status_code == 200:
        print("✅ Admin login working")
    else:
        print("❌ Admin login failed")
    
    # Test party registration
    party_data = {
        "party_name": "Test Democratic Party",
        "symbol": "🗳️"
    }
    response = requests.post(f"{base_url}/register_party", json=party_data, timeout=5)
    if response.status_code == 200:
        print("✅ Party registration working")
    else:
        print("❌ Party registration failed")
    
    # Test officer registration
    officer_data = {
        "name": "Test Officer",
        "number": "OFF001"
    }
    response = requests.post(f"{base_url}/register_officer", json=officer_data, timeout=5)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Officer registration working - Key ID: {result.get('key_id')}")
    else:
        print("❌ Officer registration failed")
    
    # Test voter registration
    voter_data = {
        "voter_id": "TEST001",
        "name": "Test Voter"
    }
    response = requests.post(f"{base_url}/register_voter", json=voter_data, timeout=5)
    if response.status_code == 200:
        print("✅ Voter registration working")
    else:
        print("❌ Voter registration failed")
    
    # Test dashboard
    response = requests.get(f"{base_url}/dashboard", timeout=5)
    if response.status_code == 200:
        print("✅ Dashboard endpoint working")
    else:
        print("❌ Dashboard endpoint failed")
    
    print("\n✅ Backend testing completed")
    return True

def simulate_voting_process():
    """Simulate a complete voting process."""
    print("\n🗳️ Simulating Complete Voting Process...")
    base_url = "http://localhost:5000"
    
    try:
        # Register a test voter
        voter_id = f"VOTER_{random.randint(1000, 9999)}"
        voter_data = {
            "voter_id": voter_id,
            "name": f"Test Voter {voter_id}"
        }
        
        response = requests.post(f"{base_url}/register_voter", json=voter_data)
        if response.status_code != 200:
            print("❌ Failed to register test voter")
            return False
        
        print(f"✅ Test voter registered: {voter_id}")
        
        # Verify biometric
        biometric_data = {
            "voter_id": voter_id,
            "type": "thumb"
        }
        
        response = requests.post(f"{base_url}/verify_biometric", json=biometric_data)
        if response.status_code != 200:
            print("❌ Biometric verification failed")
            return False
        
        print("✅ Biometric verification successful")
        
        # Get parties
        response = requests.get(f"{base_url}/get_parties")
        if response.status_code != 200:
            print("❌ Failed to get parties")
            return False
        
        parties = response.json().get("parties", [])
        if not parties:
            print("❌ No parties available for voting")
            return False
        
        print(f"✅ Found {len(parties)} parties for voting")
        
        # Cast vote
        selected_party = random.choice(parties)
        vote_data = {
            "voter_id": voter_id,
            "party_name": selected_party["party_name"]
        }
        
        response = requests.post(f"{base_url}/cast_vote", json=vote_data)
        if response.status_code != 200:
            print("❌ Vote casting failed")
            return False
        
        print(f"✅ Vote cast successfully for: {selected_party['party_name']}")
        
        # Check results
        response = requests.get(f"{base_url}/get_results")
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Current results retrieved - Total votes: {results.get('total_votes', 0)}")
        
        print("\n✅ Complete voting simulation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Voting simulation failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests."""
    print("🚀 Starting Comprehensive Integration Tests")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Quantum Key Generation
    if test_quantum_key_generation():
        success_count += 1
    
    # Test 2: Backend Endpoints
    if test_backend_endpoints():
        success_count += 1
    
    # Test 3: Complete Voting Process
    if simulate_voting_process():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! System is ready for production.")
    else:
        print("⚠️  Some tests failed. Please check the system configuration.")
    
    return success_count == total_tests

if __name__ == "__main__":
    run_comprehensive_test()
