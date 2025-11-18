# 🚀 Google Cloud Platform Setup Guide for Team Synapse

This guide will walk you through setting up your Google Cloud Platform account and configuring it for Team Synapse step by step.

## 📋 Prerequisites

- A Google account (Gmail account works)
- A credit card (for billing verification - Google Cloud offers free tier credits)
- Basic familiarity with command line (optional, but helpful)

---

## Step 1: Create a Google Cloud Account & Project

### 1.1 Sign Up for Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **"Get started for free"** or **"Sign in"** if you already have an account
3. Complete the sign-up process
4. **Enable billing** (Google will ask for a credit card, but you get $300 free credits for 90 days)

### 1.2 Create a New Project

1. In the Google Cloud Console, click the **project dropdown** at the top
2. Click **"New Project"**
3. Enter a project name (e.g., `team-synapse`)
4. Note your **Project ID** (it will be auto-generated, e.g., `team-synapse-123456`)
   - ⚠️ **IMPORTANT:** Save this Project ID - you'll need it later!
5. Click **"Create"**
6. Wait a few seconds, then select your new project from the dropdown

---

## Step 2: Install Google Cloud SDK (gcloud CLI)

### Option A: Install via Homebrew (macOS - Recommended)

```bash
# Install gcloud CLI
brew install --cask google-cloud-sdk

# Initialize gcloud
gcloud init
```

### Option B: Manual Installation

1. Download from: https://cloud.google.com/sdk/docs/install
2. Follow the installation instructions for your OS
3. Run `gcloud init` after installation

### 2.1 Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set your project (replace YOUR_PROJECT_ID with your actual project ID)
gcloud config set project YOUR_PROJECT_ID

# Verify it's set correctly
gcloud config get-value project
```

---

## Step 3: Enable Required APIs

Team Synapse needs two Google Cloud APIs:

1. **Vertex AI API** - for Gemini AI model access
2. **Cloud Storage API** - for storing audio files

### 3.1 Enable APIs via Console (Easiest)

1. Go to [API Library](https://console.cloud.google.com/apis/library)
2. Search for **"Vertex AI API"** and click it
3. Click **"Enable"**
4. Go back to API Library
5. Search for **"Cloud Storage API"** and click it
6. Click **"Enable"**

### 3.2 Enable APIs via Command Line (Alternative)

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

---

## Step 4: Create a Google Cloud Storage Bucket

A bucket is like a folder in the cloud where your audio files will be temporarily stored.

### 4.1 Create Bucket via Console

1. Go to [Cloud Storage](https://console.cloud.google.com/storage)
2. Click **"Create Bucket"**
3. Enter a **bucket name** (must be globally unique)
   - Example: `team-synapse-audio-123456` (add random numbers)
   - ⚠️ **Bucket names must be lowercase, no spaces, globally unique**
4. Choose a **location type**: "Region"
5. Select a **location**: `us-central1` (or your preferred region)
6. Choose **"Standard"** storage class
7. Click **"Create"**

### 4.2 Create Bucket via Command Line

```bash
# Replace YOUR_BUCKET_NAME with a unique name
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME

# Example:
# gsutil mb -l us-central1 gs://team-synapse-audio-123456
```

⚠️ **Save your bucket name** - you'll need it for configuration!

---

## Step 5: Create a Service Account

A service account is like a "robot user" that your application uses to access Google Cloud services.

### 5.1 Create Service Account via Console

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"Create Service Account"**
3. Enter details:
   - **Service account name**: `team-synapse`
   - **Service account ID**: (auto-filled, e.g., `team-synapse`)
   - **Description**: "Service account for Team Synapse application"
4. Click **"Create and Continue"**
5. **Grant roles** (click "Select a role" for each):
   - `Vertex AI User` (for Gemini AI access)
   - `Storage Object Admin` (for GCS bucket access)
6. Click **"Continue"** then **"Done"**

### 5.2 Create Service Account via Command Line

```bash
# Replace YOUR_PROJECT_ID with your actual project ID
export PROJECT_ID="YOUR_PROJECT_ID"

# Create service account
gcloud iam service-accounts create team-synapse \
    --display-name="Team Synapse Service Account" \
    --project=$PROJECT_ID

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:team-synapse@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Grant Storage Object Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:team-synapse@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

---

## Step 6: Create and Download Service Account Key

This key file allows your application to authenticate with Google Cloud.

### 6.1 Download Key via Console

1. Go to [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click on your `team-synapse` service account
3. Go to the **"Keys"** tab
4. Click **"Add Key"** > **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. The JSON file will download automatically
8. **Move this file** to your project directory:
   ```bash
   # Move the downloaded file to your project
   mv ~/Downloads/YOUR_PROJECT_ID-*.json ~/Desktop/team-synapse/service-account-key.json
   ```

### 6.2 Download Key via Command Line

```bash
# Replace YOUR_PROJECT_ID with your actual project ID
export PROJECT_ID="YOUR_PROJECT_ID"

# Create and download key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=team-synapse@${PROJECT_ID}.iam.gserviceaccount.com \
    --project=$PROJECT_ID
```

⚠️ **IMPORTANT SECURITY NOTE:**
- Never commit this key file to Git (it's already in `.gitignore`)
- Keep it secure and don't share it publicly
- If it's ever exposed, delete it and create a new one

---

## Step 7: Configure Environment Variables

### 7.1 Create .env File

1. Copy the example file:
   ```bash
   cd ~/Desktop/team-synapse
   cp .env.example .env
   ```

2. Open `.env` in your editor:
   ```bash
   nano .env
   # or
   code .env
   ```

3. Fill in your values:

```bash
# Replace with YOUR actual values
VERTEX_PROJECT_ID=your-actual-project-id
VERTEX_LOCATION=us-central1
GCS_BUCKET_NAME=your-actual-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/Users/ajaysingh/Desktop/team-synapse/service-account-key.json
```

**Example with real values:**
```bash
VERTEX_PROJECT_ID=team-synapse-123456
VERTEX_LOCATION=us-central1
GCS_BUCKET_NAME=team-synapse-audio-123456
GOOGLE_APPLICATION_CREDENTIALS=/Users/ajaysingh/Desktop/team-synapse/service-account-key.json
```

### 7.2 Verify Configuration

You can verify your configuration by checking:

```bash
# Check if .env file exists and has values
cat .env

# Verify service account key exists
ls -la service-account-key.json
```

---

## Step 8: Test Your Setup

### 8.1 Install Python Dependencies

```bash
# Make sure you're in the project directory
cd ~/Desktop/team-synapse

# Create virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 8.2 Test GCP Connection

Create a simple test script to verify everything works:

```bash
# Test script (you can run this in Python)
python3 << EOF
import os
from google.cloud import storage
import vertexai

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test GCS connection
try:
    client = storage.Client()
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    bucket = client.bucket(bucket_name)
    print(f"✅ GCS connection successful! Bucket: {bucket_name}")
except Exception as e:
    print(f"❌ GCS connection failed: {e}")

# Test Vertex AI connection
try:
    vertexai.init(
        project=os.getenv("VERTEX_PROJECT_ID"),
        location=os.getenv("VERTEX_LOCATION")
    )
    print(f"✅ Vertex AI connection successful!")
except Exception as e:
    print(f"❌ Vertex AI connection failed: {e}")
EOF
```

### 8.3 Run the Application

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the app
python app.py
```

If everything is configured correctly, you should see:
```
Starting Team Synapse application...
Configuration validated successfully
Project ID: your-project-id
GCS Bucket: your-bucket-name
Gemini Model: gemini-1.5-pro-002
Launching Gradio interface...
```

The app will be available at: `http://localhost:7860`

---

## 🐛 Troubleshooting

### Error: "GCS_BUCKET_NAME is not set"
- Make sure your `.env` file exists and has `GCS_BUCKET_NAME` set
- Check that the bucket name matches exactly (case-sensitive)

### Error: "Authentication failed" or "Credentials not found"
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check that the service account key file exists at that path
- Try using an absolute path instead of relative path

### Error: "API not enabled"
- Go to [API Library](https://console.cloud.google.com/apis/library)
- Search for "Vertex AI API" and "Cloud Storage API"
- Make sure both are enabled

### Error: "Permission denied" or "Access denied"
- Verify your service account has the correct roles:
  - `Vertex AI User` (roles/aiplatform.user)
  - `Storage Object Admin` (roles/storage.objectAdmin)
- Check IAM permissions in the console

### Error: "Bucket not found"
- Verify the bucket name is correct (case-sensitive)
- Make sure the bucket exists in the correct project
- Check that you're using the right project ID

---

## 📝 Quick Reference Checklist

- [ ] Google Cloud account created and billing enabled
- [ ] Project created and Project ID saved
- [ ] gcloud CLI installed and authenticated
- [ ] Vertex AI API enabled
- [ ] Cloud Storage API enabled
- [ ] GCS bucket created (name saved)
- [ ] Service account created (`team-synapse`)
- [ ] Service account has `Vertex AI User` role
- [ ] Service account has `Storage Object Admin` role
- [ ] Service account key JSON file downloaded
- [ ] Key file moved to project directory
- [ ] `.env` file created with correct values
- [ ] Test connection successful
- [ ] Application runs without errors

---

## 🎉 You're All Set!

Once you've completed all steps, your Team Synapse application should be ready to:
- Upload meeting audio files
- Store them temporarily in Google Cloud Storage
- Analyze them with Google Gemini AI
- Extract structured information (action items, decisions, people, etc.)

If you encounter any issues, refer to the troubleshooting section above or check the main README.md file.

---

## 💰 Cost Estimation

**Free Tier:**
- Vertex AI: First 60 requests/month free
- Cloud Storage: 5GB free storage, 5,000 Class A operations/month

**Estimated Costs (beyond free tier):**
- Gemini API: ~$0.001-0.01 per audio file (depends on length)
- Cloud Storage: ~$0.02 per GB/month
- **Total for typical usage: < $5/month**

Google Cloud provides $300 free credits for new accounts (valid for 90 days), which should be more than enough for testing and development.

