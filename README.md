# 🎙️ Echo Voice Agent (LiveKit)

A real-time voice agent built with LiveKit that joins a room, listens to the user's audio, and echoes it back after ~1 second delay. Built for the Revrag Tech Hiring Assignment.

---

## 📋 What This Project Does

- Joins a LiveKit room as an agent
- Listens to the user speaking
- Echoes the user's audio back after ~1 second
- **Never speaks while the user is speaking** (uses Silero VAD)
- **Stops immediately if the user interrupts** during echo playback
- **Plays a beep reminder** if no speech is detected for 20+ seconds

---

## 🛠️ Requirements

Before starting, make sure you have:

- **Python 3.10 or higher** installed → Download from https://www.python.org/downloads/
- **A LiveKit Cloud account (free)** → Sign up at https://cloud.livekit.io
- **Git** installed → Download from https://git-scm.com

---

## ⚙️ Setup Instructions (Step by Step)

### Step 1: Clone the Repository

Open your terminal (Command Prompt or PowerShell on Windows) and run:

```bash
git clone https://github.com/YOUR_USERNAME/echo-voice-agent.git
cd echo-voice-agent
```

### Step 2: Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it on Windows
venv\Scripts\activate

# Activate it on Mac/Linux
source venv/bin/activate
```

> ✅ You should see `(venv)` at the start of your terminal line after activation.

### Step 3: Install Dependencies

```bash
pip install livekit livekit-agents livekit-api livekit-plugins-silero python-dotenv "numpy<2" onnxruntime==1.17.3
```

> ⚠️ This may take 1-2 minutes. Wait for it to finish completely.

### Step 4: Get Your LiveKit Credentials

1. Go to **https://cloud.livekit.io** and log in
2. Open your project
3. Click **Settings → Keys** in the left sidebar
4. Copy these 3 values:
   - **WebSocket URL** (starts with `wss://`)
   - **API Key** (starts with `API`)
   - **API Secret** (long string)

### Step 5: Create the `.env` File

In your terminal (inside the project folder), run:

```bash
# On Windows
(
echo LIVEKIT_URL=wss://your-project.livekit.cloud
echo LIVEKIT_API_KEY=your_api_key_here
echo LIVEKIT_API_SECRET=your_api_secret_here
) > .env
```

```bash
# On Mac/Linux
cat > .env << EOF
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
EOF
```

> ⚠️ Replace the values with your real credentials from LiveKit Cloud.

Verify it looks correct:
```bash
# Windows
type .env

# Mac/Linux
cat .env
```

---

## ▶️ How to Run

### Step 1: Activate virtual environment (every time you open a new terminal)

```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 2: Start the agent

```bash
python agent.py
```

You should see:
```
🔌 Connecting to wss://...
✅ Connected to LiveKit room!
🤖 Agent started, setting up audio track...
✅ Audio track published
✅ VAD loaded
🎧 Waiting for someone to join the room...
⏰ Silence checker running...
```

### Step 3: Join the room to test

1. Go to **https://agents-playground.livekit.io**
2. Enter your LiveKit credentials (URL, API Key, API Secret)
3. Set the room name to match what's in `agent.py` (default: `echo-room`)
4. Click **Connect**
5. Allow microphone access in your browser
6. **Speak something!**

### Step 4: What to expect

| You do | Agent does |
|--------|------------|
| Speak a sentence | Agent listens and buffers your audio |
| Stop speaking | Agent waits 1 second |
| Stay quiet | Agent plays your audio back to you |
| Speak while agent is echoing | Agent stops echoing immediately |
| Stay silent for 20+ seconds | Agent plays a short beep reminder |

---

## 🔐 Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LIVEKIT_URL` | Your LiveKit Cloud WebSocket URL | `wss://myproject.livekit.cloud` |
| `LIVEKIT_API_KEY` | Your LiveKit API Key | `APIabc123` |
| `LIVEKIT_API_SECRET` | Your LiveKit API Secret | `abcdefgh1234567890` |

> ⚠️ Never commit your `.env` file to GitHub. It is already in `.gitignore`.

---

## 📦 SDK and Libraries Used

| Library | Purpose |
|---------|---------|
| `livekit` | Core LiveKit Python SDK for room connection |
| `livekit-agents` | Agent framework |
| `livekit-api` | Access token generation |
| `livekit-plugins-silero` | Silero VAD for voice activity detection |
| `python-dotenv` | Load environment variables from `.env` file |
| `numpy` | Audio sample generation (reminder tone) |
| `onnxruntime` | Required by Silero VAD to run the ML model |

---

## 🌐 External Services

| Service | Purpose | Cost |
|---------|---------|------|
| LiveKit Cloud | Real-time audio room infrastructure | Free tier available |

No OpenAI or other paid services required.

---

## 🧠 How No-Overlap Works

The agent uses **Silero VAD (Voice Activity Detection)** to detect when the user is speaking in real time.

**State machine:**

```
User speaks → is_user_speaking = True
           → if agent is echoing → cancel echo task immediately

User stops  → is_user_speaking = False
           → capture buffered frames
           → wait 1 second
           → play echo only if user is NOT speaking

During echo → check is_user_speaking before each frame
           → if user speaks → break out of echo loop immediately
```

This ensures:
- ✅ Agent never speaks while user is speaking
- ✅ Echo is cancelled the moment user starts talking
- ✅ Uses explicit state flags (`is_user_speaking`, `is_agent_speaking`)

---

## ⏰ How Silence Handling Works

A background async task (`_silence_checker`) runs every 5 seconds and checks:

```python
elapsed = time.time() - last_speech_time
if elapsed >= 20 seconds and user is not speaking and agent is not speaking:
    play reminder tone (once)
    reset timer
```

- ✅ Fires only once per silence period (not continuously)
- ✅ Timer resets after the reminder plays
- ✅ Does not fire until a real participant has joined the room

---

## ⚠️ Known Limitations

- Only handles **one user at a time** cleanly (multiple users may cause mixed audio buffers)
- The silence reminder is a **beep tone** (not a voice message) since no TTS service is used
- Slight echo latency depending on network conditions
- The agent must be restarted if it disconnects from the room
- Room name is hardcoded in `agent.py` — change it to match your playground room name

---

## 📁 Project Structure

```
echo-voice-agent/
├── agent.py        # Main agent code
├── .env            # Your credentials (never commit this!)
├── .gitignore      # Ignores venv and .env
└── README.md       # This file
```
<img width="1500" height="753" alt="Screenshot 2026-02-24 214946" src="https://github.com/user-attachments/assets/65c40b48-dca0-46b0-8f63-d4d3e7253505" />

<img width="1919" height="1035" alt="Screenshot 2026-02-24 194728" src="https://github.com/user-attachments/assets/2683952b-0e0e-41bb-9a3f-75ccfe7b5ce4" />
