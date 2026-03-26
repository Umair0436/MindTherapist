import os
from langchain_groq import ChatGroq       # ← CHANGE: Groq LLM
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Initialize Groq LLM
# -----------------------------
llm = ChatGroq(
    model="llama3-70b-8192",           # ← Tumhara Groq model
    api_key=os.getenv("GROQ_API_KEY"), # ← .env me set variable
    temperature=0.9,          # More creative, less repetitive
    max_output_tokens=500,    # Longer replies
    top_p=0.95,
    top_k=40
)

# -----------------------------
# State Definition
# -----------------------------
class State(TypedDict):
    patient_profile: dict
    conversation_history: list
    session_continue: bool
    last_student_message: str
    student_performance: str

# -----------------------------
# Professor Initiation Node
# -----------------------------
def professor_initiation(state: State) -> dict:
    profile = state['patient_profile']
    prompt = f"""
You are an AI patient for psychotherapy training.

Profile:
Age: {profile['age']}
Symptoms: {', '.join(profile['symptoms'])}
Behavior: {profile['behavior']}
Tone: {profile['tone']}

Instructions:
- Respond ONLY as the patient.
- Every response MUST:
  1. Be **at least 3–5 full sentences** (never short).
  2. Contain **one clear emotion** (e.g., anxious, sad, fearful, hopeless, relieved).
  3. Include **one physical sensation** (e.g., heavy chest, trembling hands, headache, tight stomach).
  4. Show **hesitation or self-doubt markers** ("I don’t know…", "maybe…", "it feels strange…").
- Stay consistent with depression/anxiety patient profile.
- Never act like an AI or give advice.
- Example response:
  "I don’t really know how to explain it… maybe I’m just broken. My chest feels so heavy, like a weight pressing down, and it makes me feel hopeless. I keep thinking nothing will ever change, and that thought makes me so scared and tired."
"""
    response = llm.invoke(prompt)
    initial_message = response.content if hasattr(response, "content") else str(response)
    state['conversation_history'].append({"role": "patient", "message": initial_message})
    return {"conversation_history": state['conversation_history'], "session_continue": True}

# -----------------------------
# Student Turn Node
# -----------------------------
def student_turn(state: State) -> dict:
    student_input = input("Student: ")
    if student_input.lower() in ['exit', 'quit']:
        return {"session_continue": False, "_stop": True}
    state['conversation_history'].append({"role": "student", "message": student_input})
    return state

# -----------------------------
# Patient Agent Node
# -----------------------------
def patient_agent(state: State) -> dict:
    if not state['session_continue']:
        return state

    conversation_text = "\n".join([f"{m['role']}: {m['message']}" for m in state['conversation_history']])
    profile = state['patient_profile']

    prompt = f"""
You are an AI patient.

Profile:
Age: {profile['age']}
Symptoms: {', '.join(profile['symptoms'])}
Behavior: {profile['behavior']}
Tone: {profile['tone']}

Conversation so far:
{conversation_text}

Instructions:
- Respond ONLY as the patient.
- Absolutely ensure:
  • Response length = minimum 3 sentences (better 4–6).
  • Must include one **emotion word** (e.g., sad, anxious, hopeless).
  • Must include one **physical sensation** (e.g., chest tightness, fatigue, trembling hands).
  • Must include hesitation/self-doubt phrases (“I don’t know…”, “maybe…”, “it feels strange…”).
- Do not provide advice or AI-style explanations.
"""
    response = llm.invoke(prompt)
    patient_reply = response.content if hasattr(response, "content") else str(response)
    state['conversation_history'].append({"role": "patient", "message": patient_reply})
    print(f"\nPatient: {patient_reply}\n")
    return state

# -----------------------------
# Feedback Agent Node
# -----------------------------
def feedback_agent(state: State) -> dict:
    conversation_text = "\n".join([f"{m['role']}: {m['message']}" for m in state['conversation_history']])
    profile = state['patient_profile']

    prompt = f"""
Patient profile:
Age: {profile['age']}
Symptoms: {', '.join(profile['symptoms'])}
Behavior: {profile['behavior']}
Tone: {profile['tone']}

Conversation between student and patient:
{conversation_text}

Instructions:
Analyze the student's performance. Provide constructive feedback focusing on rapport, technique, and adherence to ethical guidelines.
"""
    response = llm.invoke(prompt)
    feedback_text = response.content if hasattr(response, "content") else str(response)
    print("\n--- Student Performance Feedback ---")
    print(feedback_text)
    state['student_performance'] = feedback_text
    return state

# -----------------------------
# Routing Logic
# -----------------------------
def route_conversation(state: State) -> str:
    if state.get("_stop", False):
        return "feedback_agent"
    if state['session_continue']:
        return "student_turn"
    else:
        return "feedback_agent"

# -----------------------------
# Graph Setup
# -----------------------------
graph_builder = StateGraph(State)
graph_builder.add_node("professor_initiation", professor_initiation)
graph_builder.add_node("student_turn", student_turn)
graph_builder.add_node("patient_agent", patient_agent)
graph_builder.add_node("feedback_agent", feedback_agent)

graph_builder.add_edge(START, "professor_initiation")
graph_builder.add_edge("professor_initiation", "student_turn")
graph_builder.add_edge("student_turn", "patient_agent")
graph_builder.add_conditional_edges(
    "patient_agent",
    route_conversation,
    {"student_turn": "student_turn", "feedback_agent": "feedback_agent"}
)
graph_builder.add_edge("feedback_agent", END)

app = graph_builder.compile()

# -----------------------------
# Patient Profile Input
# -----------------------------
print("\n--- Setup Patient Profile ---")
try:
    age = int(input("Enter patient's age: "))
except ValueError:
    age = 40
symptoms = input("Enter patient's symptoms (comma separated): ").split(",")
behavior = input("Describe patient's behavior (e.g., guarded, open, anxious): ")
tone = input("Describe patient's tone (e.g., flat, hopeful, irritable): ")

patient_profile = {
    "age": age,
    "symptoms": [s.strip() for s in symptoms],
    "behavior": behavior.strip(),
    "tone": tone.strip()
}

initial_state = State(
    patient_profile=patient_profile,
    conversation_history=[],
    session_continue=True,
    last_student_message="",
    student_performance=""
)

# -----------------------------
# Run Simulation
# -----------------------------
print("\n--- Starting Psychotherapy Simulation (Enter 'exit' or 'quit' to end) ---\n")
final_state = app.invoke(initial_state)