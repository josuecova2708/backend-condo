#!/usr/bin/env python3
"""
CORS Diagnostic Script para Railway + Vercel
Testea todas las configuraciones CORS críticas
"""
import requests
import json
from urllib.parse import urljoin

# Configuración
BACKEND_URL = "https://backend-condo-production.up.railway.app"
FRONTEND_URL = "https://frontend-condo.vercel.app"

def test_preflight_options():
    """Test preflight OPTIONS request"""
    print("🧪 Testing preflight OPTIONS request...")

    headers = {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,authorization'
    }

    try:
        response = requests.options(
            f"{BACKEND_URL}/api/auth/login/",
            headers=headers,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print("Response Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower() or 'cors' in key.lower():
                print(f"  {key}: {value}")

        # Check critical headers
        required_headers = [
            'access-control-allow-origin',
            'access-control-allow-methods',
            'access-control-allow-headers'
        ]

        missing_headers = []
        for header in required_headers:
            if header not in [h.lower() for h in response.headers.keys()]:
                missing_headers.append(header)

        if missing_headers:
            print(f"❌ Missing headers: {missing_headers}")
        else:
            print("✅ All critical CORS headers present")

        return response

    except Exception as e:
        print(f"❌ Preflight test failed: {e}")
        return None

def test_actual_request():
    """Test actual POST request"""
    print("\n🧪 Testing actual POST request...")

    headers = {
        'Origin': FRONTEND_URL,
        'Content-Type': 'application/json'
    }

    data = {
        'email': 'test@example.com',
        'password': 'testpassword'
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login/",
            headers=headers,
            json=data,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print("CORS Headers in Response:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower():
                print(f"  {key}: {value}")

        return response

    except Exception as e:
        print(f"❌ Actual request test failed: {e}")
        return None

def test_health_endpoint():
    """Test health endpoint (usually doesn't require CORS)"""
    print("\n🧪 Testing health endpoint...")

    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Backend is alive")
        return response
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return None

def main():
    print("🚀 CORS Diagnostic Tool - Railway + Vercel")
    print("=" * 50)
    print(f"Backend: {BACKEND_URL}")
    print(f"Frontend: {FRONTEND_URL}")
    print("=" * 50)

    # Test 1: Health check
    health_response = test_health_endpoint()

    # Test 2: Preflight OPTIONS
    preflight_response = test_preflight_options()

    # Test 3: Actual request
    actual_response = test_actual_request()

    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)

    if health_response and health_response.status_code == 200:
        print("✅ Backend is reachable")
    else:
        print("❌ Backend is not reachable")

    if preflight_response and preflight_response.status_code == 200:
        print("✅ Preflight request successful")
    else:
        print("❌ Preflight request failed")

    if actual_response:
        if actual_response.status_code in [200, 400, 401]:  # 400/401 are OK for CORS (auth might fail)
            print("✅ Actual request reaches backend (CORS working)")
        else:
            print(f"❌ Actual request failed with status {actual_response.status_code}")
    else:
        print("❌ Actual request completely failed")

    # Instructions
    print("\n" + "=" * 50)
    print("🔧 NEXT STEPS")
    print("=" * 50)

    if not preflight_response or preflight_response.status_code != 200:
        print("1. Check CORS_ALLOW_METHODS includes OPTIONS")
        print("2. Verify corsheaders.middleware.CorsMiddleware is first in MIDDLEWARE")
        print("3. Check Railway logs for CORS errors")

    print("4. Update Railway environment variables:")
    print("   - Remove CORS_ALLOW_ALL_ORIGINS=True")
    print("   - Keep CORS_ALLOWED_ORIGINS with specific domains")

if __name__ == "__main__":
    main()