#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/roman/ai_bootcamp_backend/aibc_auth')

from passlib.context import CryptContext

# Test bcrypt functionality
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_password_verification():
    password = "SecurePass123!"
    
    # Generate hash
    hashed = pwd_context.hash(password)
    print(f"Generated hash: {hashed}")
    
    # Test verification
    result = pwd_context.verify(password, hashed)
    print(f"Verification result: {result}")
    
    # Test with database hash
    db_hash = "$2b$12$KXlizq6Ny95D0Synd2UNF./GIJHREVWm6Wj5TAWBP6rVrirRh6Fre"
    result2 = pwd_context.verify(password, db_hash)
    print(f"Database hash verification: {result2}")
    
    return result and result2

if __name__ == "__main__":
    try:
        success = test_password_verification()
        print(f"All tests passed: {success}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)