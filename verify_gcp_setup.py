#!/usr/bin/env python3
"""
GCP Setup Verification Script for Team Synapse

This script verifies that your Google Cloud Platform setup is correct.
Run this after completing the GCP setup steps.
"""
import os
import sys
from pathlib import Path

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install it with: pip install python-dotenv")
    print("   Continuing without .env file support...\n")

def check_env_vars():
    """Check if required environment variables are set."""
    print("=" * 60)
    print("STEP 1: Checking Environment Variables")
    print("=" * 60)
    
    required_vars = {
        "VERTEX_PROJECT_ID": os.getenv("VERTEX_PROJECT_ID"),
        "GCS_BUCKET_NAME": os.getenv("GCS_BUCKET_NAME"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    }
    
    optional_vars = {
        "VERTEX_LOCATION": os.getenv("VERTEX_LOCATION", "us-central1"),
    }
    
    all_good = True
    
    for var_name, var_value in required_vars.items():
        if not var_value or var_value.startswith("YOUR_") or "HERE" in var_value:
            print(f"❌ {var_name}: Not set or using placeholder value")
            all_good = False
        else:
            print(f"✅ {var_name}: {var_value}")
    
    for var_name, var_value in optional_vars.items():
        print(f"ℹ️  {var_name}: {var_value}")
    
    print()
    return all_good, required_vars


def check_service_account_key(credentials_path):
    """Check if service account key file exists."""
    print("=" * 60)
    print("STEP 2: Checking Service Account Key File")
    print("=" * 60)
    
    if not credentials_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    key_path = Path(credentials_path)
    
    if not key_path.exists():
        print(f"❌ Service account key file not found: {credentials_path}")
        print(f"   Expected at: {key_path.absolute()}")
        return False
    
    if not key_path.is_file():
        print(f"❌ Path exists but is not a file: {credentials_path}")
        return False
    
    # Check if it's valid JSON
    try:
        import json
        with open(key_path, 'r') as f:
            key_data = json.load(f)
        
        if "type" not in key_data or key_data.get("type") != "service_account":
            print("⚠️  File exists but doesn't look like a service account key")
            return False
        
        project_id = key_data.get("project_id", "unknown")
        print(f"✅ Service account key file found")
        print(f"   Project ID in key: {project_id}")
        print(f"   Key type: {key_data.get('type')}")
        return True
    except json.JSONDecodeError:
        print("❌ Service account key file is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading service account key: {e}")
        return False


def check_gcs_connection(bucket_name):
    """Check Google Cloud Storage connection."""
    print("=" * 60)
    print("STEP 3: Testing Google Cloud Storage Connection")
    print("=" * 60)
    
    try:
        from google.cloud import storage
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Try to access bucket
        if bucket.exists():
            print(f"✅ GCS bucket exists: {bucket_name}")
            return True
        else:
            print(f"❌ GCS bucket not found: {bucket_name}")
            print("   Make sure the bucket name is correct and exists in your project")
            return False
            
    except ImportError:
        print("❌ google-cloud-storage not installed")
        print("   Install with: pip install google-cloud-storage")
        return False
    except Exception as e:
        print(f"❌ GCS connection failed: {e}")
        print("   Check your credentials and bucket name")
        return False


def check_vertex_ai_connection(project_id, location):
    """Check Vertex AI connection."""
    print("=" * 60)
    print("STEP 4: Testing Vertex AI Connection")
    print("=" * 60)
    
    try:
        import vertexai
        
        vertexai.init(project=project_id, location=location)
        print(f"✅ Vertex AI initialized successfully")
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        return True
        
    except ImportError:
        print("❌ vertexai not installed")
        print("   Install with: pip install vertexai")
        return False
    except Exception as e:
        print(f"❌ Vertex AI connection failed: {e}")
        print("   Make sure:")
        print("   1. Vertex AI API is enabled in your project")
        print("   2. Your service account has 'Vertex AI User' role")
        print("   3. Project ID and location are correct")
        return False


def check_apis_enabled(project_id):
    """Check if required APIs are enabled."""
    print("=" * 60)
    print("STEP 5: Checking Required APIs (Optional)")
    print("=" * 60)
    
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            print("⚠️  Skipping API check (no credentials)")
            return True
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        service = build('serviceusage', 'v1', credentials=credentials)
        
        required_apis = [
            'aiplatform.googleapis.com',  # Vertex AI
            'storage.googleapis.com',     # Cloud Storage
        ]
        
        all_enabled = True
        for api in required_apis:
            try:
                name = f"projects/{project_id}/services/{api}"
                response = service.services().get(name=name).execute()
                state = response.get('state', 'UNKNOWN')
                
                if state == 'ENABLED':
                    print(f"✅ {api}: Enabled")
                else:
                    print(f"❌ {api}: {state}")
                    all_enabled = False
            except Exception as e:
                print(f"⚠️  Could not check {api}: {e}")
        
        return all_enabled
        
    except ImportError:
        print("⚠️  google-api-python-client not installed, skipping API check")
        print("   Install with: pip install google-api-python-client")
        return True
    except Exception as e:
        print(f"⚠️  Could not check APIs: {e}")
        return True  # Don't fail the whole check if API check fails


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("Team Synapse - GCP Setup Verification")
    print("=" * 60 + "\n")
    
    results = []
    
    # Step 1: Check environment variables
    env_ok, env_vars = check_env_vars()
    results.append(("Environment Variables", env_ok))
    print()
    
    if not env_ok:
        print("❌ Please fix environment variable issues before continuing")
        print("   See GCP_SETUP.md for instructions\n")
        return False
    
    # Step 2: Check service account key
    credentials_path = env_vars.get("GOOGLE_APPLICATION_CREDENTIALS")
    key_ok = check_service_account_key(credentials_path)
    results.append(("Service Account Key", key_ok))
    print()
    
    if not key_ok:
        print("❌ Please fix service account key issues before continuing\n")
        return False
    
    # Step 3: Check GCS connection
    bucket_name = env_vars.get("GCS_BUCKET_NAME")
    gcs_ok = check_gcs_connection(bucket_name)
    results.append(("GCS Connection", gcs_ok))
    print()
    
    # Step 4: Check Vertex AI connection
    project_id = env_vars.get("VERTEX_PROJECT_ID")
    location = os.getenv("VERTEX_LOCATION", "us-central1")
    vertex_ok = check_vertex_ai_connection(project_id, location)
    results.append(("Vertex AI Connection", vertex_ok))
    print()
    
    # Step 5: Check APIs (optional)
    api_ok = check_apis_enabled(project_id)
    results.append(("APIs Enabled", api_ok))
    print()
    
    # Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 All checks passed! Your GCP setup is correct.")
        print("   You can now run: python app.py")
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        print("   Refer to GCP_SETUP.md for detailed setup instructions.")
    
    print()
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

