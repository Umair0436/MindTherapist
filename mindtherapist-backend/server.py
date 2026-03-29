from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session as DBSession
from dotenv import load_dotenv
import uuid
import json
import re
import requests
import os
import io

# Import database setup and models
from database import init_db, get_db, TherapySession, Message, Report

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

app = FastAPI()

# Create all database tables on startup if they don't exist yet
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Helper Functions ----

def get_groq_response(messages, system_prompt):
    """Call Groq API and return the AI reply"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    groq_messages = []
    if system_prompt:
        groq_messages.append({"role": "system", "content": system_prompt})

    for m in messages:
        role = "assistant" if m['role'] == 'patient' else "user"
        groq_messages.append({"role": role, "content": m['message']})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": groq_messages,
        "temperature": 0.9,
        "max_tokens": 500,
        "top_p": 0.95
    }

    try:
        res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        result = res.json()
        if 'error' in result:
            return None, result['error']['message']
        text = result['choices'][0]['message']['content']
        return text, None
    except Exception as e:
        return None, str(e)


def extract_json_from_reply(reply: str) -> dict:
    """Safely extract JSON from Groq reply"""
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', reply, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def draw_wrapped_text(pdf, text, x, y, page_height, max_width=450, line_height=16):
    """Draw long text with word wrap"""
    from reportlab.lib.utils import simpleSplit
    lines = simpleSplit(text, "Helvetica", 11, max_width)
    for line in lines:
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = page_height - 50
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def check_y(pdf, y, page_height, margin=60):
    """Create new page if y too low"""
    if y < margin:
        pdf.showPage()
        return page_height - 50
    return y


# ---- Pydantic Models ----

class PatientProfile(BaseModel):
    age: int
    symptoms: List[str]
    behavior: str
    tone: str

class ChatMessage(BaseModel):
    session_id: str
    message: str

class EndSession(BaseModel):
    session_id: str

class DirectChat(BaseModel):
    messages: list
    system_prompt: str
    session_id: Optional[str] = None  # Optional — used to save messages to DB


# ---- Endpoints ----

@app.get("/")
def root():
    return FileResponse("../index.html")


@app.post("/session/start")
def start_session(profile: PatientProfile, db: DBSession = Depends(get_db)):
    session_id = str(uuid.uuid4())

    new_session = TherapySession(
        id=session_id,
        age=profile.age,
        symptoms=json.dumps(profile.symptoms),
        behavior=profile.behavior,
        tone=profile.tone,
        is_active=True
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {"session_id": session_id, "message": "Session started"}


@app.post("/session/end")
def end_session(data: EndSession, db: DBSession = Depends(get_db)):
    session = db.query(TherapySession).filter(TherapySession.id == data.session_id).first()

    if not session:
        return {"error": "Session not found"}

    session.is_active = False
    db.commit()

    return {"message": "Session ended"}


@app.post("/chat")
def chat(data: ChatMessage, db: DBSession = Depends(get_db)):
    session = db.query(TherapySession).filter(TherapySession.id == data.session_id).first()

    if not session:
        return {"error": "Session not found"}

    student_msg = Message(
        session_id=data.session_id,
        role="student",
        message=data.message
    )
    db.add(student_msg)
    db.commit()

    all_messages = db.query(Message)\
        .filter(Message.session_id == data.session_id)\
        .order_by(Message.timestamp)\
        .all()

    history = [{"role": m.role, "message": m.message} for m in all_messages]

    symptoms_list = json.loads(session.symptoms)
    system_prompt = f"""You are an AI patient.
Age: {session.age}
Symptoms: {symptoms_list}
Behavior: {session.behavior}
Tone: {session.tone}"""

    reply, error = get_groq_response(history, system_prompt)
    if error:
        return {"error": error}

    patient_msg = Message(
        session_id=data.session_id,
        role="patient",
        message=reply
    )
    db.add(patient_msg)
    db.commit()

    return {"reply": reply}


@app.post("/direct-chat")
def direct_chat(data: DirectChat, db: DBSession = Depends(get_db)):
    """Direct Groq call — saves messages to DB if session_id is provided"""
    reply, error = get_groq_response(data.messages, data.system_prompt)
    if error:
        return {"error": error}

    # Save to DB if session_id provided
    if data.session_id:
        try:
            # Save all messages from this turn (avoid duplicates by saving only last student message)
            if data.messages:
                last_msg = data.messages[-1]
                # Only save if it's a student message (not the initial intro prompt)
                if last_msg['role'] == 'student':
                    student_msg = Message(
                        session_id=data.session_id,
                        role="student",
                        message=last_msg['message']
                    )
                    db.add(student_msg)

            # Always save patient reply
            patient_msg = Message(
                session_id=data.session_id,
                role="patient",
                message=reply
            )
            db.add(patient_msg)
            db.commit()
        except Exception as e:
            # Don't fail the chat if DB save fails
            print(f"DB save error: {e}")

    return {"reply": reply}


def _generate_report(session_id: str, db: DBSession):
    """Generate report from DB history and save to reports table"""
    session = db.query(TherapySession).filter(TherapySession.id == session_id).first()
    if not session:
        return None, "Session not found"

    all_messages = db.query(Message)\
        .filter(Message.session_id == session_id)\
        .order_by(Message.timestamp)\
        .all()

    history = [{"role": m.role, "message": m.message} for m in all_messages]

    system_prompt = """You are an expert psychotherapy supervisor.
Analyze the conversation and provide response in this exact JSON format:
{
    "scores": {
        "overall": 0-100,
        "rapport": 0-100,
        "technique": 0-100,
        "ethics": 0-100
    },
    "summary": "...",
    "strengths": ["...", "..."],
    "improvements": ["...", "..."],
    "next_steps": "..."
}
Only return the JSON. No extra text, no markdown.
"""
    reply, error = get_groq_response(history, system_prompt)
    if error:
        return None, error

    report_data = extract_json_from_reply(reply)
    if not report_data:
        return None, "Failed to parse report from AI response"

    new_report = Report(
        session_id=session_id,
        scores_json=json.dumps(report_data["scores"]),
        summary=report_data["summary"],
        strengths=json.dumps(report_data.get("strengths", [])),
        improvements=json.dumps(report_data.get("improvements", [])),
        next_steps=report_data["next_steps"]
    )
    db.add(new_report)
    db.commit()

    return report_data, None


@app.get("/report/{session_id}")
def get_report(session_id: str, db: DBSession = Depends(get_db)):
    report_data, error = _generate_report(session_id, db)
    if error:
        return {"error": error}
    return {"report": report_data}


@app.get("/report/{session_id}/download")
def download_report(session_id: str, db: DBSession = Depends(get_db)):
    report_data, error = _generate_report(session_id, db)
    if error:
        return {"error": error}

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "MindTherapist Session Report")
    y -= 40

    pdf.setFont("Helvetica-Bold", 12)
    y = check_y(pdf, y, height)
    pdf.drawString(50, y, "Scores:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for key, value in report_data["scores"].items():
        y = check_y(pdf, y, height)
        pdf.drawString(70, y, f"{key.capitalize()}: {value}/100")
        y -= 18

    y -= 10
    y = check_y(pdf, y, height)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Summary:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    y = draw_wrapped_text(pdf, report_data["summary"], 70, y, height)

    y -= 10
    y = check_y(pdf, y, height)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Strengths:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for item in report_data.get("strengths", []):
        y = draw_wrapped_text(pdf, f"- {item}", 70, y, height)

    y -= 10
    y = check_y(pdf, y, height)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Improvements:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for item in report_data.get("improvements", []):
        y = draw_wrapped_text(pdf, f"- {item}", 70, y, height)

    y -= 10
    y = check_y(pdf, y, height)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Next Steps:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    y = draw_wrapped_text(pdf, report_data["next_steps"], 70, y, height)

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"}
    )


@app.get("/sessions/history")
def get_all_sessions(db: DBSession = Depends(get_db)):
    all_sessions = db.query(TherapySession).order_by(TherapySession.created_at.desc()).all()
    result = []
    for s in all_sessions:
        msg_count = db.query(Message).filter(Message.session_id == s.id).count()
        result.append({
            "session_id": s.id,
            "age": s.age,
            "is_active": s.is_active,
            "message_count": msg_count,
            "created_at": str(s.created_at)
        })
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)