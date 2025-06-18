#!/usr/bin/env python3
"""Test script to debug pool controller connection."""

import sys
from pycompool import PoolController

def test_connection(host, port=8899):
    """Test connection to pool controller."""
    device = f"socket://{host}:{port}"
    print(f"Testing connection to {device}")
    
    try:
        controller = PoolController(device, 9600)
        print("PoolController created successfully")
        
        print("Calling get_status()...")
        status = controller.get_status()
        
        print(f"Status type: {type(status)}")
        print(f"Status value: {status}")
        print(f"Status bool: {bool(status)}")
        
        if status:
            print("✅ Connection successful!")
            return True
        else:
            print("❌ Connection failed - no status data")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_connection.py <host> [port]")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8899
    
    test_connection(host, port)