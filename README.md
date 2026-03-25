# 🧠 MindTherapist

**AI-powered psychotherapy simulation platform for practitioner training.**

MindTherapist lets psychology students and therapists-in-training practice real patient interactions with an AI-simulated patient — before working with real clients. Sessions are fully logged, scored, and exportable as PDF reports.


## ✨ Features

- 🤖 **AI Patient Simulation** — Powered by Groq (LLaMA 3.3 70B). Configure patient age, symptoms, behavior, and tone before each session.
- 💬 **Real-time Chat Interface** — Conduct a full therapy session with the AI patient in a clean chat UI.
- 📊 **Session Reports** — After each session, get an AI-generated supervisor report with scores for rapport, technique, ethics, and overall performance.
- 📄 **PDF Download** — Download the full session report as a formatted PDF.
- 🗄️ **Persistent Database** — All sessions, messages, and reports are saved to SQLite via SQLAlchemy — no data lost on server restart.
- 📁 **Session History** — View all past sessions with message counts and timestamps via the `/sessions/history` endpoint.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | FastAPI (Python) |
| AI Model | Groq API — LLaMA 3.3 70B Versatile |
| Database | SQLite + SQLAlchemy ORM |
| PDF Generation | ReportLab |
| Deployment | Render (backend) + Netlify (frontend) |

---

## 📁 Project Structure

```
MindTherapist/
├── index.html                  # Frontend — full single-page app
├── mindtherapist-backend/
│   ├── server.py               # FastAPI backend — all endpoints
│   ├── database.py             # SQLAlchemy models and DB setup
│   ├── mindtherapist.db        # SQLite database (auto-created)
│   ├── .env                    # Environment variables (not committed)
│   └── requirements.txt        # Python dependencies
```

---

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Umair0436/MindTherapist.git
cd MindTherapist
```

### 2. Set up the backend

```bash
cd mindtherapist-backend
python -m pip install -r requirements.txt
```

### 3. Create `.env` file

```
GROQ_API_KEY=your_groq_api_key_here
```

Get your free API key at [console.groq.com](https://console.groq.com)

### 4. Run the backend

```bash
uvicorn server:app --reload
```

Backend will start at `http://127.0.0.1:8000`

### 5. Open the frontend

Open `index.html` directly in your browser or use Live Server in VS Code.

---

## 📡 API Endpoints

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session/start` | Start a new therapy session |
| POST | `/session/end` | End an active session |
| GET | `/sessions/history` | Get all past sessions |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send a message and get AI patient reply |
| POST | `/direct-chat` | Direct Groq call bypassing session system |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/report/{session_id}` | Get session report as JSON |
| GET | `/report/{session_id}/download` | Download session report as PDF |

---

### `/session/start` Request Body

```json
{
  "age": 28,
  "symptoms": ["anxiety", "insomnia", "social withdrawal"],
  "behavior": "avoidant",
  "tone": "quiet and hesitant"
}
```

### `/chat` Request Body

```json
{
  "session_id": "your-session-uuid",
  "message": "How have you been feeling lately?"
}
```

---

## 🗄️ Database Schema

**sessions** — stores patient profile and session status
**messages** — stores every message exchanged in a session
**reports** — stores AI-generated supervisor reports after each session

All tables are auto-created on first server startup.

---

## 📦 Requirements

```
fastapi
uvicorn
groq
requests
python-dotenv
sqlalchemy
reportlab
```

Install all:

```bash
python -m pip install -r requirements.txt
```

---

## 👤 Author

**Muhammad Umair**
AI Developer — YumTech, Lahore
[GitHub](https://github.com/Umair0436) • [LinkedIn](https://linkedin.com/in/muhammad-umair-dev)

---

## 📄 License

MIT License — free to use and modify.