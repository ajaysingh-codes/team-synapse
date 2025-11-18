# 🧠 Team Synapse - Corporate Memory AI

**Phase 1-3 Implementation:** Audio Ingestion & Analysis Pipeline

Transform meeting recordings into structured, actionable intelligence using Google Gemini AI.

## 🎯 What This Does

Team Synapse automatically:
- **Transcribes** meeting audio with high accuracy
- **Extracts** action items, decisions, and key information
- **Identifies** people, clients, and projects mentioned
- **Structures** everything as JSON for knowledge graph integration

## 🏗️ Architecture

```
├── app.py                      # Main Gradio application
├── config.py                   # Configuration management
├── services/
│   ├── gcs_service.py         # Google Cloud Storage
│   ├── gemini_service.py      # Gemini AI analysis
│   └── ingestion_pipeline.py # Orchestration
├── ui/
│   ├── theme.py               # Custom Gradio theme
│   └── components.py          # Reusable UI components
└── utils/
    └── logger.py              # Logging utilities
```

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Python 3.9+** installed
3. **Git** installed

### Step 1: Clone & Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd team-synapse

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Google Cloud Setup

#### 2.1 Create a Google Cloud Project

```bash
# Go to: https://console.cloud.google.com
# Create a new project or select existing one
```

#### 2.2 Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com
```

#### 2.3 Create a GCS Bucket

```bash
# Create a bucket for temporary audio storage
gsutil mb -l us-central1 gs://your-unique-bucket-name
```

#### 2.4 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create team-synapse \
    --display-name="Team Synapse Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:team-synapse@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:team-synapse@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Download key file
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=team-synapse@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Step 3: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
nano .env
```

Update these values in `.env`:
```bash
VERTEX_PROJECT_ID=your-actual-project-id
GCS_BUCKET_NAME=your-actual-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Step 4: Run the Application

```bash
python app.py
```

The app will be available at: `http://localhost:7860`

## 🎬 How to Use

### Option 1: Upload a Recording

1. Go to the **"📁 Upload File"** tab
2. Click to upload an audio file (MP3, WAV, M4A, OGG)
3. Click **"🚀 Analyze Recording"**
4. Wait 30-60 seconds for analysis
5. View results in the JSON panel

### Option 2: Record Live

1. Go to the **"🎤 Record Live"** tab
2. Click the microphone icon to start recording
3. Speak a summary of a meeting (30-60 seconds recommended)
4. Click **"🚀 Analyze Recording"**
5. View results

### Sample Test Recording Script

Record yourself saying:
```
This is a Project Phoenix kickoff meeting. Sarah Johnson will handle 
the design work and deliver mockups by next Friday. We decided to use 
React for the frontend and discussed this with our client, Acme Corporation. 
John from Acme had concerns about the timeline, but overall the sentiment 
was positive. The key decision was to prioritize mobile-first design.
```

## 📊 What Gets Extractedß

The system extracts:

- ✅ **Action Items** with assignees and due dates
- 🎯 **Key Decisions** made during the meeting
- 👥 **People** mentioned
- 🏢 **Clients/Companies** discussed
- 📊 **Projects** referenced
- 📝 **Full Transcript** of the meeting
- 😊 **Sentiment** analysis
- 📋 **Meeting Summary**

## 🎨 Custom Theme

The application features a professional enterprise theme with:
- Modern gradient design
- Responsive layout
- Dark mode support
- Accessible color contrast
- Smooth animations

## 🔧 Configuration Options

Edit `config.py` or use environment variables:

```python
# Gemini Model
GEMINI_MODEL=gemini-1.5-pro-002

# Temperature (0.0 - 1.0, lower = more deterministic)
GEMINI_TEMPERATURE=0.1

# Max file size in MB
MAX_FILE_SIZE_MB=100

# Logging level
LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

### Error: "GCS_BUCKET_NAME is not set"
- Make sure you created a GCS bucket
- Update the `GCS_BUCKET_NAME` in your `.env` file

### Error: "Authentication failed"
- Verify your service account key file path is correct
- Check that the service accoßunt has the required permissions
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to the correct file

### Error: "API not enabled"
- Enable the Vertex AI API: `gcloud services enable aiplatform.googleapis.com`
- Enable the Cloud Storage API: `gcloud services enable storage.googleapis.com`

### Upload fails or times out
- Check your internet connection
- Verify the audio file is under 100MB
- Try with a shorter audio file first (30 seconds)

## 📈 Next Steps (Phase 4+)

This is Phase 1-3 of the complete Team Synapse system. Coming next:

- **Phase 4:** Neo4j knowledge graph integration
- **Phase 5:** MCP servers for Miro, Notion, ElevenLabs
- **Phase 6:** Context-aware action dashboard with Google ADK

## 🏆 Hackathon Submission

This project is built for the **MCP 1-Year Anniversary Hackathon**:
- **Track:** Agent App - Productivity
- **Awards:** Google Gemini Award, Modal Innovation Award

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This is a hackathon project, but contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 💬 Support

For issues or questions:
- Open an issue on GitHub
- Check the troubleshooting section above

---

**Built with ❤️ using Google Gemini, Vertex AI, and Gradio**