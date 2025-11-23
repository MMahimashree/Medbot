# medbot_app.py (updated: patient chat widened, simple login, WhatsApp-style chat colors)
import os
import json
import random
import joblib
import pandas as pd
import streamlit as st
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import time
import html

# -----------------------------
# Page config + basic theme
# -----------------------------
st.set_page_config(page_title="MedBot", page_icon="🩺", layout="wide")

CHAT_CSS = """
<style>
:root{
  --card-bg: #ffffff;
  --muted: #6c757d;
  --accent: #0b74de;
  --success: #28a745;
  --danger: #dc3545;
  --soft: rgba(11,116,222,0.06);
  --glass: rgba(255,255,255,0.85);
}

/* basic card / bubble styles */
.app-card {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 6px 18px rgba(10,20,40,0.04);
  border: 1px solid rgba(10,15,30,0.03);
  margin-bottom: 12px;
}
.header-space { height: 18px; }

/* WhatsApp-like chat bubbles */
/* User bubble (right) - WhatsApp green */
.user-bubble {
  background: #c6f6d5;  /* light green bubble */
  color: #000000;       /* black text */
  padding: 12px 16px;
  border-radius: 14px;
  margin: 8px 0;
  max-width: 78%;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border: 1px solid rgba(0,0,0,0.04);
  font-size: 1rem;
}


/* Bot bubble (left) - light neutral */
.bot-bubble {
  display: inline-block;
  max-width: 78%;
  background: #f1f0f0; /* light grey similar to chat apps */
  border-radius: 18px;
  padding: 10px 14px;
  margin: 6px 0;
  color: #051428; /* dark text */
  box-shadow: 0 6px 18px rgba(10,20,40,0.03);
  align-self: flex-start;
  word-wrap: break-word;
  line-height: 1.35;
}

/* small meta label above bubbles */
.meta { font-size: 11px; color: var(--muted); margin-bottom: 6px; }

/* history card */
.history-card {
  border-radius: 10px;
  padding: 10px;
  border: 1px solid rgba(10,15,30,0.04);
  margin-bottom: 10px;
  background: linear-gradient(180deg, rgba(255,255,255,1), rgba(250,252,255,1));
}
.status-dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:8px; vertical-align:middle; }

/* status pills */
.status-pill { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:600; background:rgba(0,0,0,0.04); }
.status-accepted { background: rgba(40,167,69,0.12); color: #166534; }
.status-rejected { background: rgba(220,53,69,0.10); color: #7a1f2b; }
.status-pending { background: rgba(255,193,7,0.10); color: #6b4f00; }

/* ensure content sits above blobs if present */
.app-card, .history-card, .bot-bubble, .user-bubble, .stButton, .stTextInput {
  position: relative;
  z-index: 2;
}

/* responsive tweaks */
@media (max-width: 800px) {
  .bot-bubble, .user-bubble { max-width: 94%; }
}
</style>
"""

st.markdown(CHAT_CSS, unsafe_allow_html=True)

# Limit main content width & style a centered login card
NARROW_CSS = """
<style>
.block-container {
  max-width: 760px;    /* default; admin view overrides later when admin logged in */
  margin-left: auto;
  margin-right: auto;
  padding-left: 18px;
  padding-right: 18px;
}
.login-card {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 8px 30px rgba(10,20,40,0.06);
  border: 1px solid rgba(10,15,30,0.03);
  margin: 12px auto;
  max-width: 720px;
}
@media (max-width:800px){
  .block-container { padding-left: 8px; padding-right: 8px; max-width: 98vw; }
  .login-card { padding: 12px; }
}
</style>
"""
st.markdown(NARROW_CSS, unsafe_allow_html=True)

# Background hero (kept in CSS but we'll hide the flashy parts via SIMPLE_LOGIN_CSS)
BG_CSS = """
<style>
.login-hero {
  position: fixed;
  inset: 0;
  z-index: 0; /* behind content & blobs */
  background-image: linear-gradient(180deg, rgba(250,253,255,0.85), rgba(255,255,255,0.95)), url("login_bg.svg");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  pointer-events: none;
}
.login-card { position: relative; z-index: 2; }
.login-card::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255,255,255,0.6), rgba(255,255,255,0.5));
  pointer-events: none;
  z-index: -1;
}

/* floating blurred blobs (decorative) */
:root { --blob-1: rgba(11,116,222,0.10); --blob-2: rgba(45,165,255,0.08); }
.bg-blob {
  position: fixed;
  border-radius: 50%;
  filter: blur(40px);
  transform: translate3d(0,0,0);
  pointer-events: none;
  z-index: 0;
  mix-blend-mode: screen;
}
.bg-blob.b1 { width: 480px; height: 480px; left: -140px; top: -140px; background: var(--blob-1); animation: float1 12s ease-in-out infinite; }
.bg-blob.b2 { width: 360px; height: 360px; right: -100px; bottom: -80px; background: var(--blob-2); animation: float2 14s ease-in-out infinite; }

@keyframes float1 {
  0% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(20px) rotate(12deg); }
  100% { transform: translateY(0) rotate(0deg); }
}
@keyframes float2 {
  0% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-14px) rotate(-8deg); }
  100% { transform: translateY(0) rotate(0deg); }
}
</style>
"""
st.markdown(BG_CSS, unsafe_allow_html=True)

# --- SIMPLE LOGIN CSS: hide flashy decorations and make login card plain/clean ---
SIMPLE_LOGIN_CSS = """
<style>
/* hide the large background hero and decorative blobs for a minimal login */
.login-hero { display: none !important; }
.bg-blob { display: none !important; }

/* simpler login card visuals */
.login-card {
  background: #ffffff !important;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.06);
  border: 1px solid rgba(0,0,0,0.05);
}
</style>
"""
st.markdown(SIMPLE_LOGIN_CSS, unsafe_allow_html=True)

# NOTE: we intentionally DO NOT render the login hero or blob elements to remove flashy visuals.

# -----------------------------
# Load model + jsons
# -----------------------------
try:
    model = joblib.load("medbot_model.pkl")
    vectorizer = joblib.load("vectorizer.pkl")

    with open("intents.json", "r", encoding="utf-8") as f:
        intents = json.load(f)

    with open("doctors.json", "r", encoding="utf-8") as f:
        doctors = json.load(f)

    with open("symptoms.json", "r", encoding="utf-8") as f:
        symptoms = json.load(f)

    if os.path.exists("follow_up_questions.json"):
        with open("follow_up_questions.json", "r", encoding="utf-8") as f:
            follow_ups = json.load(f)
    else:
        follow_ups = {}

    doctors_df = pd.DataFrame(doctors)

    le = LabelEncoder()
    tags = [intent['tag'] for intent in intents.get('intents', [])]
    if tags:
        le.fit(tags)
except FileNotFoundError as e:
    st.error(f"Missing file: {e}. Place your model and JSONs in the same folder.")
    st.stop()
except Exception as e:
    st.error(f"Error loading resources: {e}")
    st.stop()

# -----------------------------
# helper: normalize username
# -----------------------------
def _normalize_username(name: str) -> str:
    s = "".join(ch for ch in str(name).lower() if ch.isalnum() or ch == "_")
    return s.replace(" ", "_")

# -----------------------------
# build demo user store (doctors + demo users)
# -----------------------------
users = {
    "admin_user": {"password": "admin_pass", "role": "Admin"},
    "patient_user": {"password": "patient_pass", "role": "Patient"},
}
# build users from doctors_df but ensure username is a string (avoid NaN/float keys)
for _, row in doctors_df.iterrows():
    if isinstance(row, pd.Series):
        raw_uname = row.get("username")
        if pd.notna(raw_uname) and str(raw_uname).strip() != "":
            uname = str(raw_uname).strip()
        else:
            uname = _normalize_username(str(row.get("name", "")))
        users[uname] = {"password": "doctor_pass", "role": "Doctor", "display_name": row.get("name")}

# keep doctor list sorted and all keys as strings
doctor_usernames = sorted([u for u, meta in users.items() if meta.get("role") == "Doctor"], key=lambda s: str(s).lower())
doctor_rows = [{"username": u, "name": users[u].get("display_name", u)} for u in doctor_usernames]

# helper mapping display->username
_display_to_uname = {}
for u, meta in users.items():
    if meta.get("role") == "Doctor":
        disp = meta.get("display_name") or u
        key = "".join(ch for ch in str(disp).lower() if ch.isalnum())
        _display_to_uname[key] = u

# -----------------------------
# specialty map
# -----------------------------
specialty_map = {
    "fever": "General Physician",
    "cough": "General Physician",
    "cold": "ENT",
    "headache": "Neurologist",
    "back pain": "Orthopedic",
    "stomach pain": "Gastroenterologist",
    "nausea": "Gastroenterologist",
    "vomiting": "Gastroenterologist",
    "dizziness": "Neurologist",
    "fatigue": "General Physician",
    "chest pain": "Cardiologist",
    "shortness of breath": "Cardiologist",
    "allergy": "Allergist",
    "sore throat": "ENT",
    "diarrhea": "Gastroenterologist",
    "constipation": "Gastroenterologist",
    "joint pain": "Orthopedic",
    "muscle pain": "Orthopedic",
    "rash": "Dermatologist",
    "insomnia": "Psychiatrist",
    "anxiety": "Psychiatrist",
    "depression": "Psychiatrist",
    "weight loss": "Endocrinologist",
    "weight gain": "Endocrinologist",
    "blurred vision": "Ophthalmologist",
    "ear pain": "ENT",
    "eye pain": "Ophthalmologist",
    "urination problem": "Nephrologist",
    "hair fall": "Dermatologist",
    "memory loss": "Neurologist",
    "heartburn": "Gastroenterologist",
    "gas problem": "Gastroenterologist",
    "cold hands": "General Physician",
    "cold feet": "General Physician",
    "sweating": "General Physician",
    "thirst": "Endocrinologist",
    "frequent urination": "Endocrinologist",
    "coughing blood": "Pulmonologist",
    "nose bleeding": "ENT",
    "swelling": "Nephrologist",
    "lump": "Oncologist",
    "chest tightness": "Cardiologist",
    "palpitations": "Cardiologist",
    "loss of appetite": "General Physician",
    "vomiting blood": "Gastroenterologist",
    "confusion": "Neurologist",
    "feeling cold": "General Physician",
    "feeling hot": "General Physician",
    "difficulty swallowing": "ENT",
    "snoring": "ENT",
    "gas trouble": "Gastroenterologist",
    "heart attack": "Cardiologist",
    "acid reflux": "Gastroenterologist",
    "heart pain": "Cardiologist",
    "skin discoloration": "Dermatologist",
    "itching": "Dermatologist",
    "acne": "Dermatologist",
    "hearing loss": "ENT",
    "ringing in ears": "ENT",
    "tonsil pain": "ENT",
    "child not eating": "Pediatrician",
    "delayed milestones": "Pediatrician",
    "bone fracture": "Orthopedic",
    "knee stiffness": "Orthopedic",
    "bloating": "Gastroenterologist",
    "mood swings": "Psychiatrist",
    "panic attacks": "Psychiatrist",
    "chronic cough": "Pulmonologist",
    "wheezing": "Pulmonologist",
    "hormonal imbalance": "Endocrinologist",
    "irregular periods": "Endocrinologist",
    "kidney pain": "Nephrologist",
    "foamy urine": "Nephrologist",
    "eye redness": "Ophthalmologist",
    "double vision": "Ophthalmologist",
    "joint swelling": "Rheumatologist",
    "morning stiffness": "Rheumatologist",
    "unexplained bruising": "Oncologist",
    "persistent fatigue": "Oncologist",
    "seasonal sneezing": "Allergist",
    "skin allergy": "Allergist",
    "irregular heartbeat": "Cardiologist",
    "chest heaviness": "Cardiologist"
}

APPT_CSV = "appointments.csv"
HISTORY_CSV = "patient_history.csv"

# -----------------------------
# appointment persistence
# -----------------------------
def load_appointments():
    if os.path.exists(APPT_CSV):
        try:
            return pd.read_csv(APPT_CSV).to_dict("records")
        except Exception:
            return []
    return []

def save_appointments(appts):
    try:
        if not appts:
            open(APPT_CSV, "w").close()
        else:
            pd.DataFrame(appts).to_csv(APPT_CSV, index=False)
        if 'appointments' in st.session_state:
            st.session_state.appointments = appts
    except Exception as e:
        st.error(f"Failed to save appointments: {e}")

def book_appointment(patient_id, doctor_name, doctor_username, time_slot, symptom):
    appt = {
        "patient": patient_id,
        "doctor": doctor_name,
        "doctor_username": doctor_username,
        "time": time_slot,
        "symptom": symptom,
        "status": "Pending",
        "created_at": datetime.utcnow().isoformat()
    }
    appts = load_appointments()
    appts.append(appt)
    save_appointments(appts)
    if 'appointments' not in st.session_state:
        st.session_state.appointments = []
    st.session_state.appointments.append(appt)
    return appt

def get_patient_appointments(patient_id):
    return [a for a in load_appointments() if a.get("patient") == patient_id]

def get_latest_patient_appointment(patient_id):
    appts = get_patient_appointments(patient_id)
    if not appts:
        return None
    try:
        appts_sorted = sorted(appts, key=lambda x: x.get("created_at") or "", reverse=True)
        return appts_sorted[0]
    except Exception:
        return appts[-1]

def get_doctor_appointments(doctor_id):
    appts = load_appointments()
    return [a for a in appts if a.get("doctor_username") == doctor_id]

def update_appointment_status(patient, doctor_identifier, time_slot, new_status):
    appts = load_appointments()
    updated = False
    for a in appts:
        if a.get("patient") == patient and a.get("doctor_username") == doctor_identifier and a.get("time") == time_slot:
            a["status"] = new_status
            updated = True
            break
    if updated:
        save_appointments(appts)
    return updated

# -----------------------------
# patient visit history helpers
# -----------------------------
def get_patient_visit_history(patient_id):
    """Return past visits for a patient (Accepted or Completed)."""
    appts = load_appointments()
    visits = [a for a in appts if a.get("patient") == patient_id and a.get("status") in ("Accepted", "Completed")]
    try:
        visits_sorted = sorted(visits, key=lambda x: x.get("created_at") or "", reverse=True)
    except Exception:
        visits_sorted = visits
    return visits_sorted

def mark_appointment_completed(patient, doctor_username, time_slot):
    """Set appointment status to Completed and append to history CSV."""
    appts = load_appointments()
    changed = False
    for a in appts:
        if a.get("patient") == patient and a.get("doctor_username") == doctor_username and a.get("time") == time_slot:
            a["status"] = "Completed"
            changed = True
            break
    if changed:
        save_appointments(appts)
        # Append to history CSV for permanent record
        record = {
            "patient": patient,
            "doctor_username": doctor_username,
            "time": time_slot,
            "symptom": a.get("symptom"),
            "completed_at": datetime.utcnow().isoformat()
        }
        try:
            if os.path.exists(HISTORY_CSV):
                df = pd.read_csv(HISTORY_CSV)
                df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
            else:
                df = pd.DataFrame([record])
            df.to_csv(HISTORY_CSV, index=False)
        except Exception:
            pass
    return changed

# -----------------------------
# helper functions (bot + doctor rec)
# -----------------------------
def find_specialty(symptom):
    symptom_lower = str(symptom).lower().strip()
    if symptom_lower in specialty_map:
        return specialty_map[symptom_lower]
    for key in specialty_map:
        if key in symptom_lower or symptom_lower in key:
            return specialty_map[key]
    return "General Physician"

def get_bot_response(user_input):
    """
    Predict intent -> return (reply_from_responses, predicted_tag_or_None, follow_ups_list_or_None)
    Important: do NOT use follow-up text as the immediate bot reply.
    """
    try:
        vec = vectorizer.transform([user_input.lower()])
        prediction = model.predict(vec)
        predicted_tag = le.inverse_transform(prediction)[0] if hasattr(le, "inverse_transform") else prediction[0]
    except Exception:
        predicted_tag = None

    if predicted_tag:
        for intent in intents.get('intents', []):
            if intent.get('tag') == predicted_tag:
                # reply must come from intent['responses'] only
                resp_choices = intent.get('responses') or []
                response = random.choice(resp_choices) if resp_choices else "Sorry, I don't understand."
                # collect follow-ups separately (always return list or None)
                raw_fups = None
                if predicted_tag in follow_ups:
                    raw_fups = follow_ups[predicted_tag]
                else:
                    raw_fups = intent.get('follow_up_questions')
                # normalize follow-ups to list of non-empty strings or None
                fups = None
                if isinstance(raw_fups, (list, tuple)):
                    cleaned = [str(x).strip() for x in raw_fups if str(x).strip()]
                    fups = cleaned if cleaned else None
                elif isinstance(raw_fups, str) and raw_fups.strip():
                    fups = [raw_fups.strip()]
                return response, predicted_tag, fups
    return "Sorry, I don't understand. Please describe your symptom clearly.", None, None

def recommend_doctors(symptom, top_n=3):
    specialties = find_specialty(symptom)
    if isinstance(specialties, str):
        specialties = [specialties]
    filtered = doctors_df[doctors_df['specialty'].isin(specialties)]
    sorted_docs = filtered.sort_values(by='rating', ascending=False) if not filtered.empty else doctors_df.sort_values(by='rating', ascending=False)
    top_docs = []
    for _, r in sorted_docs.head(top_n).iterrows():
        slots = r.get('slots', []) if isinstance(r.get('slots', []), list) else [s.strip() for s in str(r.get('slots', "")).split(',') if s.strip()]
        uname = r.get('username') if 'username' in r and pd.notna(r.get('username')) else _normalize_username(str(r.get('name', '')))
        top_docs.append({"name": r.get('name'), "specialty": r.get('specialty'), "rating": r.get('rating'), "slots": slots, "username": uname})
    return top_docs

# -----------------------------
# session init
# -----------------------------
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'role' not in st.session_state: st.session_state.role = None
if 'username' not in st.session_state: st.session_state.username = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []  # list of {"user": str or None, "bot": str or None}
if 'current_symptom' not in st.session_state: st.session_state.current_symptom = None
# follow-up state (queue + pending + answers)
if 'follow_up_queue' not in st.session_state: st.session_state.follow_up_queue = []  # remaining questions
if 'pending_follow_up' not in st.session_state: st.session_state.pending_follow_up = None  # current question displayed and waiting for answer
if 'follow_up_answers' not in st.session_state: st.session_state.follow_up_answers = {}
if 'asking_follow_up' not in st.session_state: st.session_state.asking_follow_up = False
if 'symptoms_collected' not in st.session_state: st.session_state.symptoms_collected = []
if 'appointments' not in st.session_state: st.session_state.appointments = load_appointments()
# UI: patient history toggle
if 'show_history' not in st.session_state: st.session_state.show_history = False

# -----------------------------
# UI helpers: chat bubbles (escape input)
# -----------------------------
def _render_user_bubble(text):
    if text is None:
        return
    safe = html.escape(str(text)).replace("\n", "<br>")
    st.markdown(f"<div style='display:flex; justify-content:flex-end;'><div class='user-bubble'><div class='meta'>You</div>{safe}</div></div>", unsafe_allow_html=True)

def _render_bot_bubble(text):
    if text is None:
        return
    safe = html.escape(str(text)).replace("\n", "<br>")
    st.markdown(f"<div style='display:flex; justify-content:flex-start;'><div class='bot-bubble'><div class='meta'>MedBot</div>{safe}</div></div>", unsafe_allow_html=True)

def _render_history_card(appt):
    # appt: dict with patient, doctor, time, created_at, status, symptom
    name = appt.get("patient")
    doctor = appt.get("doctor") or appt.get("doctor_username")
    # created_at may be ISO timestamp; show date if possible
    created = appt.get("created_at")
    date_str = ""
    try:
        if created:
            dt = datetime.fromisoformat(created)
            date_str = dt.strftime("%Y-%m-%d")
    except Exception:
        date_str = created or ""
    time_slot = appt.get("time", "")
    status = appt.get("status", "Pending")
    # color dot + label
    if isinstance(status, str) and status.lower() in ("accepted", "approved"):
        dot_color = "#28a745"  # green
        status_label = "Approved"
    elif isinstance(status, str) and status.lower() in ("rejected",):
        dot_color = "#dc3545"  # red
        status_label = "Rejected"
    elif isinstance(status, str) and status.lower() in ("completed",):
        dot_color = "#007bff"  # blue
        status_label = "Completed"
    else:
        dot_color = "#ffc107"  # yellow
        status_label = "Pending"

    html_card = f"""
    <div class="history-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-weight:700; font-size:1rem;">{html.escape(str(name or ""))}</div>
          <div class="small-muted">Doctor: {html.escape(str(doctor or ""))}</div>
        </div>
        <div style="text-align:right">
          <div style="font-weight:600;">{html.escape(date_str)}</div>
          <div class="small-muted">{html.escape(str(time_slot or ""))}</div>
        </div>
      </div>
      <div style="margin-top:8px;">
        <span class="status-dot" style="background:{dot_color};"></span>
        <span style="font-weight:600;">{status_label}</span>
      </div>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)

# -----------------------------
# UI: Header / Login
# -----------------------------
st.markdown("<div class='header-space'></div>", unsafe_allow_html=True)
st.title("🩺 MedBot Healthcare Assistant")

if not st.session_state.logged_in:
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    st.subheader("Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        user_type = st.selectbox("Login as", ["Patient", "Doctor", "Admin"])
    with col2:
        username_input = ""
        if user_type == "Doctor" and doctor_rows:
            doc_names = [r["name"] for r in doctor_rows]
            sel = st.selectbox("Select your name (or choose 'Type username')", ["Type username"] + doc_names, key="doctor_choice")
            if sel != "Type username":
                selected_uname = next((r["username"] for r in doctor_rows if r["name"] == sel), "")
                st.text_input("Username (autofilled)", value=selected_uname, disabled=True, key="doctor_autofill")
                username_input = selected_uname
            else:
                username_input = st.text_input("Username (or full name)")
        else:
            username_input = st.text_input("Username")
        password = st.text_input("Password", type="password")

    # Login handler (DO NOT output </div> inside this if)
    if st.button("Login"):
        username = username_input.strip() if isinstance(username_input, str) else username_input
        if not username:
            st.error("Please enter a username.")
        else:
            if user_type == "Patient":
                if username in users:
                    if users[username]["password"] == password and users[username]["role"] == "Patient":
                        st.session_state.logged_in = True
                        st.session_state.role = "Patient"
                        st.session_state.username = username
                        st.success(f"Logged in as {username} (Patient)")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                else:
                    users[username] = {"password": password, "role": "Patient"}
                    st.session_state.logged_in = True
                    st.session_state.role = "Patient"
                    st.session_state.username = username
                    st.success(f"Registered & logged in as {username} (Patient)")
                    st.rerun()
            else:
                actual_username = None
                if username in users:
                    actual_username = username
                else:
                    key = "".join(ch for ch in str(username).lower() if ch.isalnum())
                    actual_username = _display_to_uname.get(key)
                if actual_username and actual_username in users and users[actual_username]["password"] == password and users[actual_username]["role"] == user_type:
                    st.session_state.logged_in = True
                    st.session_state.role = user_type
                    st.session_state.username = actual_username
                    st.success(f"Logged in as {actual_username} ({user_type})")
                    st.rerun()
                else:
                    hint = " Use the dropdown to pick your name or type your username. Demo doctor password: 'doctor_pass'." if user_type == "Doctor" else ""
                    st.error("Invalid credentials or role mismatch." + hint)

    # CLOSE login-card wrapper here (after handling login, outside the button block)
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.sidebar.success(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# -----------------------------
# PATIENT DASHBOARD (modified width: chat area larger)
# -----------------------------
if st.session_state.logged_in and st.session_state.role == "Patient":
    st.subheader(f"Welcome, {st.session_state.username}!")
    # Wider patient dashboard chat area (changed from [3,1] to [5,1])
    col_chat, col_side = st.columns([10, 1])

    with col_chat:
        st.markdown("### 💬 Chat with MedBot")
        # render history (chat bubbles)
        for chat in st.session_state.chat_history:
            if chat.get("user"):
                _render_user_bubble(chat['user'])
            if chat.get("bot"):
                _render_bot_bubble(chat['bot'])

        # follow-up handling (single pending question + queue, no duplicates)
        if st.session_state.asking_follow_up and st.session_state.pending_follow_up:
            q = st.session_state.pending_follow_up
            # ensure question appears in chat history exactly once
            if not any(chat.get("bot") == q for chat in st.session_state.chat_history):
                st.session_state.chat_history.append({"user": None, "bot": q})
            ans = st.text_input(q, key=f"fup_{hash(q)}")
            if st.button("Answer", key=f"ans_btn_{hash(q)}") and ans.strip():
                # save user's answer once
                st.session_state.chat_history.append({"user": ans.strip(), "bot": None})
                st.session_state.follow_up_answers[q] = ans.strip()
                # move to next follow-up in queue if available
                if st.session_state.follow_up_queue:
                    st.session_state.pending_follow_up = st.session_state.follow_up_queue.pop(0)
                else:
                    # finalize follow-ups
                    st.session_state.pending_follow_up = None
                    st.session_state.asking_follow_up = False
                    symptom = st.session_state.current_symptom or " / ".join(st.session_state.follow_up_answers.values())
                    username_display = st.session_state.username or "User"
                    bot_msg = (f"Thank you, {username_display}. Based on what you’ve shared, "
                               f"it seems you’re experiencing symptoms related to {symptom}. "
                               "Here are some doctors who can help you.")
                    st.session_state.chat_history.append({"user": None, "bot": bot_msg})
                    st.session_state.symptoms_collected.append(symptom)
                    # clear follow-up buffers (keep history)
                    st.session_state.follow_up_queue = []
                    st.session_state.follow_up_answers = {}
                    st.session_state.current_symptom = None
                st.rerun()

        else:
            if not st.session_state.symptoms_collected:
                user_input = st.text_input("Describe your symptom (e.g., 'I have a fever')", key="symptom_input")
                if st.button("Send", key="send_symptom") and user_input.strip():
                    with st.spinner("MedBot is thinking..."):
                        time.sleep(0.5)
                        bot_resp, predicted_tag, fups = get_bot_response(user_input)

                    # === FIX: Avoid duplicating follow-up text as immediate bot reply ===
                    # If follow-ups exist and the chosen bot_resp matches one of them,
                    # replace bot_resp with a neutral acknowledgement so the follow-up queue
                    # will present the questions (only once).
                    if fups and any(str(bot_resp).strip() == str(q).strip() for q in fups):
                        bot_resp = "Let me ask you a few questions so I can understand your issue clearly."

                    # append user message and the immediate bot response (from intent.responses)
                    st.session_state.chat_history.append({"user": user_input.strip(), "bot": bot_resp})
                    st.session_state.current_symptom = predicted_tag or user_input.strip()
                    # if follow-ups exist, initialize queue and show first question (do NOT use follow-ups as bot reply)
                    if fups:
                        st.session_state.follow_up_queue = [str(x).strip() for x in fups if str(x).strip()]
                        st.session_state.pending_follow_up = st.session_state.follow_up_queue.pop(0) if st.session_state.follow_up_queue else None
                        st.session_state.asking_follow_up = True
                        st.session_state.follow_up_answers = {}
                        # append first follow-up once
                        first_q = st.session_state.pending_follow_up
                        if first_q and not any(chat.get("bot") == first_q for chat in st.session_state.chat_history):
                            st.session_state.chat_history.append({"user": None, "bot": first_q})
                    else:
                        # no follow-ups: finalize immediately and show doctors
                        symptom = st.session_state.current_symptom
                        username_display = st.session_state.username or "User"
                        bot_msg = (f"Thank you, {username_display}. Based on what you’ve shared, "
                                   f"it seems you’re experiencing symptoms related to {symptom}. "
                                   "Here are some doctors who can help you.")
                        st.session_state.chat_history.append({"user": None, "bot": bot_msg})
                        st.session_state.symptoms_collected.append(symptom)
                    st.rerun()
            else:
                st.markdown("### 👨‍⚕ Recommended Doctors (Top 3)")
                symptom = st.session_state.symptoms_collected[-1]
                top_docs = recommend_doctors(symptom, top_n=3)
                if top_docs:
                    for i, d in enumerate(top_docs, 1):
                        st.markdown(f"**{i}. {d['name']}**  — {d['specialty']}  — ⭐ {d['rating']}")
                    choice = st.selectbox("Select doctor to book", [f"{d['name']} ({d['specialty']})" for d in top_docs], key="doc_select")
                    selected_doc = top_docs[[f"{d['name']} ({d['specialty']})" for d in top_docs].index(choice)]
                    slot = st.selectbox("Choose available slot", selected_doc['slots'] if selected_doc['slots'] else ["Any time"], key="slot_select")
                    if st.button("Book Appointment", key="book_btn"):
                        doctor_display = selected_doc.get('name') or selected_doc.get('username')
                        doctor_username = selected_doc.get('username') or _normalize_username(doctor_display)
                        appt = book_appointment(st.session_state.username, doctor_display, doctor_username, slot, symptom)
                        st.success(f"Appointment requested with **{doctor_display}** at **{slot}**. Status: {appt['status']}")
                        st.session_state.current_symptom = None
                        st.session_state.symptoms_collected = []
                        st.session_state.follow_up_queue = []
                        st.session_state.pending_follow_up = None
                        st.session_state.follow_up_answers = {}
                        st.session_state.asking_follow_up = False
                        st.rerun()
                else:
                    st.write("No doctors found for that symptom — try rephrasing.")

        # --- NEW: After chat area, show Latest Appointment + History (moved from side) ---
        st.markdown("<div class='app-card' style='margin-top:14px'>", unsafe_allow_html=True)
        st.markdown("### 📅 Latest Appointment")
        last = get_latest_patient_appointment(st.session_state.username)
        if last:
            status = last.get("status", "Pending")
            pill_class = "status-pending"
            emoji = "⚪"
            if status == "Accepted":
                pill_class = "status-accepted"; emoji = "✅"
            elif status == "Rejected":
                pill_class = "status-rejected"; emoji = "❌"
            st.markdown(f"<div class='status-pill {pill_class}'>{emoji} {status}</div>", unsafe_allow_html=True)
            st.markdown(f"**Doctor:** {last.get('doctor') or last.get('doctor_username')}  \n**Time:** {last.get('time')}  \n**Symptom:** {last.get('symptom')}")
        else:
            st.write("No bookings yet.")
        st.markdown("</div>", unsafe_allow_html=True)

        # ====== View Appointment History (moved under chat) ======
        st.markdown("<div class='app-card' style='margin-top:10px'>", unsafe_allow_html=True)
        if st.button("📜 View Appointment History", key="view_history_btn"):
            st.session_state.show_history = not st.session_state.show_history
        if st.session_state.show_history:
            st.markdown("### 📜 Your Appointment History")
            visits = get_patient_visit_history(st.session_state.username)
            if visits:
                for v in visits:
                    _render_history_card(v)
            else:
                st.markdown("No past visits recorded.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Keep the Clear Chat button here as well
        if st.button("Clear Chat", key="clear_chat_main"):
            st.session_state.chat_history = []
            st.session_state.current_symptom = None
            st.session_state.asking_follow_up = False
            st.session_state.follow_up_queue = []
            st.session_state.pending_follow_up = None
            st.session_state.follow_up_answers = {}
            st.session_state.symptoms_collected = []
            st.rerun()

    # keep the original empty right column (or you can use it later)
    with col_side:
        # intentionally left blank so right column doesn't show duplicate content
        st.write("")

# -----------------------------
# DOCTOR DASHBOARD (view appts + mark completed; search -> single patient history)
# -----------------------------
elif st.session_state.logged_in and st.session_state.role == "Doctor":
    doc_uname = st.session_state.username

    # determine display name (reuse your existing logic)
    display_name = users.get(doc_uname, {}).get("display_name")
    if not display_name and 'username' in doctors_df.columns:
        row = doctors_df.loc[doctors_df['username'] == doc_uname]
        if not row.empty:
            display_name = row.iloc[0].get('name')
    display_name = display_name or doc_uname

    # Header exactly as requested
    st.markdown(f"**Welcome, {html.escape(str(display_name))}!**")

    # -----------------------------
    # helper: display patient history (define BEFORE it's called)
    # -----------------------------
    def _display_patient_history(patient_name):
        st.markdown(f"#### History for: {html.escape(str(patient_name))}")
        all_appts = load_appointments()

        # past accepted/completed appointments for this patient
        past = [a for a in all_appts if a.get("patient") == patient_name and a.get("status") in ("Accepted", "Completed")]

        # rows from HISTORY_CSV
        hist_rows = []
        try:
            if os.path.exists(HISTORY_CSV):
                hist_df = pd.read_csv(HISTORY_CSV)
                if not hist_df.empty and 'patient' in hist_df.columns:
                    # ensure patient column is treated as string
                    hist_rows = hist_df[hist_df['patient'].astype(str) == str(patient_name)].to_dict("records")
        except Exception:
            hist_rows = []

        # Combine and sort by created_at/completed_at descending
        combined = sorted(past + hist_rows, key=lambda x: x.get("created_at") or x.get("completed_at") or "", reverse=True)

        if not combined:
            st.write("No recorded visits found for this patient.")
            return

        for rec in combined:
            date_str = rec.get("created_at") or rec.get("completed_at") or ""
            try:
                if date_str:
                    dt = datetime.fromisoformat(date_str)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                # leave original if parsing fails
                pass
            doctor_name = rec.get("doctor") or rec.get("doctor_username") or ""
            symptom = rec.get("symptom") or ""
            status = rec.get("status") or ("Completed" if rec.get("completed_at") else "")
            st.markdown(f"- **Date:** {html.escape(str(date_str))}  \n  **Doctor:** {html.escape(str(doctor_name))}  \n  **Reason:** {html.escape(str(symptom))}  \n  **Status:** {html.escape(str(status))}")

    # -----------------------------
    # Appointments (shown immediately under header)
    # -----------------------------
    st.markdown("<div class='app-card' style='margin-top:8px'>", unsafe_allow_html=True)
    st.markdown("### Your Appointments")

    appts = get_doctor_appointments(doc_uname) or []
    if not appts:
        st.markdown("<div class='small-muted'>You have no appointments yet.</div>", unsafe_allow_html=True)
    else:
        # sort most recent first
        visible_appts = sorted(appts, key=lambda x: x.get("created_at") or "", reverse=True)
        for i, a in enumerate(visible_appts):
            status = a.get("status", "Pending")
            pill_class = "status-pending"
            emoji = "⚪"
            if isinstance(status, str) and status.lower() == "accepted":
                pill_class = "status-accepted"; emoji = "✅"
            elif isinstance(status, str) and status.lower() == "rejected":
                pill_class = "status-rejected"; emoji = "❌"
            elif isinstance(status, str) and status.lower() == "completed":
                pill_class = "status-accepted"; emoji = "✔️"

            st.markdown("<div class='app-card' style='margin-bottom:10px'>", unsafe_allow_html=True)
            st.markdown(f"**Patient:** {html.escape(str(a.get('patient') or ''))}  \n**Time:** {html.escape(str(a.get('time') or ''))}  \n**Reason:** {html.escape(str(a.get('symptom') or ''))}")
            st.markdown(f"<div class='small-muted'>Created: {html.escape(str(a.get('created_at') or ''))}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='status-pill {pill_class}' style='margin-top:8px'>{emoji} {html.escape(str(status))}</div>", unsafe_allow_html=True)

            # Action buttons: Accept / Reject / Mark Completed (no delete)
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                if status == "Pending":
                    if st.button("Accept", key=f"accept_{doc_uname}_{i}_{a.get('patient')}_{a.get('time')}"):
                        ok = update_appointment_status(a.get('patient'), doc_uname, a.get('time'), "Accepted")
                        if ok:
                            st.rerun()
                        else:
                            st.error("Failed to update appointment.")
            with c2:
                if status == "Pending":
                    if st.button("Reject", key=f"reject_{doc_uname}_{i}_{a.get('patient')}_{a.get('time')}"):
                        ok = update_appointment_status(a.get('patient'), doc_uname, a.get('time'), "Rejected")
                        if ok:
                            st.rerun()
                        else:
                            st.error("Failed to update appointment.")
            with c3:
                if status in ("Accepted",):
                    if st.button("Mark as Completed", key=f"complete_{doc_uname}_{i}_{a.get('patient')}_{a.get('time')}"):
                        ok = mark_appointment_completed(a.get('patient'), doc_uname, a.get('time'))
                        if ok:
                            st.rerun()
                        else:
                            st.error("Failed to mark completed.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------
    # Single search to view patient history (one search box under appointments)
    # -----------------------------
    st.markdown("<div class='app-card' style='margin-top:12px'>", unsafe_allow_html=True)
    st.markdown("### 🔎 View Patient History")

    search_query = st.text_input("Enter patient name or username (partial match)", key="doctor_history_search")
    if st.button("Search", key="doctor_history_search_btn"):
        q = (search_query or "").strip()
        if not q:
            st.info("Please enter a patient name or username to search.")
        else:
            # Build candidates with normalization map
            all_appts = load_appointments()
            candidates_raw = [a.get("patient") for a in all_appts if a.get("patient")]
            candidates = set([str(p).strip() for p in candidates_raw if p is not None])

            # include patients from HISTORY_CSV
            try:
                if os.path.exists(HISTORY_CSV):
                    hist_df = pd.read_csv(HISTORY_CSV)
                    if not hist_df.empty and 'patient' in hist_df.columns:
                        candidates |= set(hist_df['patient'].dropna().astype(str).str.strip().tolist())
            except Exception:
                pass

            # normalize -> map normalized -> set(originals)
            norm_map = {}
            for orig in candidates:
                norm = orig.strip().lower()
                norm_map.setdefault(norm, set()).add(orig)

            # find matches: any normalized candidate where query is substring
            q_norm = q.lower()
            matched_originals = set()
            for norm, originals in norm_map.items():
                if q_norm in norm:
                    matched_originals.update(originals)

            matches = sorted(list(matched_originals), key=lambda s: str(s).lower())

            if not matches:
                st.info("No patients found matching that query.")
            elif len(matches) > 1:
                pick = st.selectbox("Multiple matches — pick a patient", matches, key="doctor_history_pick")
                if st.button("Show History", key="doctor_history_pick_btn"):
                    _display_patient_history(pick)
            else:
                target = matches[0]
                _display_patient_history(target)

    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# ADMIN DASHBOARD (edit/delete doctor + manage appts)
# Admin-only CSS and use_container_width for tables
# -----------------------------
elif st.session_state.logged_in and st.session_state.role == "Admin":
    # --- Admin-only CSS injection (minimal & targeted) ---
    ADMIN_WIDE_CSS = """
    <style>
    /* expand the main container for admin to give more horizontal room */
    .block-container {
      max-width: 1200px !important;
      padding-left: 20px !important;
      padding-right: 20px !important;
    }
    /* make Streamlit tables expand to container width */
    .stDataFrame div[data-testid="stTable"] table, .stTable table { width: 100% !important; table-layout: auto; }
    </style>
    """
    st.markdown(ADMIN_WIDE_CSS, unsafe_allow_html=True)

    st.subheader("Admin Dashboard")
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("### 📋 All Appointments")
    all_appts = load_appointments()
    if all_appts:
        df = pd.DataFrame(all_appts)
        # use dataframe with container width so it expands in the wider admin container
        st.dataframe(df, use_container_width=True)


        st.markdown("### Manage appointment")
        options = [f"{i}: {r.get('patient')} | {r.get('doctor') or r.get('doctor_username')} | {r.get('time')} | {r.get('status')}" for i, r in enumerate(all_appts)]
        sel = st.selectbox("Select appointment", ["Select"] + options, index=0)
        if sel and sel != "Select":
            idx = int(sel.split(":", 1)[0])
            row = all_appts[idx]
            st.markdown(f"**Selected:** {row.get('patient')} — {row.get('doctor') or row.get('doctor_username')} — {row.get('time')} — {row.get('status')}")
            col_a, col_b, col_c = st.columns([1,1,1])

            # allow for any existing statuses, but provide sensible ordered list
            status_list = ["Pending", "Accepted", "Rejected", "Completed"]
            current_status = row.get("status", "Pending")
            try:
                default_index = status_list.index(str(current_status))
            except ValueError:
                # fallback: add it to the end and use that index
                status_list.append(str(current_status))
                default_index = len(status_list) - 1

            with col_a:
                new_status = st.selectbox("New status", status_list, index=default_index)
                if st.button("Update status", key=f"admin_update_{idx}"):
                    ok = update_appointment_status(row.get('patient'), row.get('doctor_username') or row.get('doctor'), row.get('time'), new_status)
                    if ok:
                        st.success("Updated.")
                        st.rerun()
                    else:
                        st.error("Failed to update.")
            with col_b:
                if st.button("Delete selected appointment", key=f"admin_delete_{idx}"):
                    appts = load_appointments()
                    try:
                        appts.pop(idx)
                        save_appointments(appts)
                        st.success("Deleted appointment.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")
            with col_c:
                days_cut = st.number_input("Delete if older than (days)", min_value=0, value=0, step=1, key="admin_delete_if_days")
                if st.button("Delete if older", key=f"admin_delete_if_{idx}"):
                    created = row.get("created_at")
                    removed = False
                    if created:
                        try:
                            dt = datetime.fromisoformat(created)
                            cutoff = datetime.utcnow() - timedelta(days=int(days_cut))
                            if dt < cutoff:
                                appts = load_appointments()
                                appts.pop(idx)
                                save_appointments(appts)
                                st.success("Deleted appointment (older than cutoff).")
                                removed = True
                        except Exception:
                            st.error("Cannot parse appointment date; aborted.")
                    if not removed and days_cut == 0:
                        st.info("No deletion: appointment not older than cutoff.")
                    if removed:
                        st.rerun()
    else:
        st.write("No appointments recorded.")
    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------
    # Admin: Add / Edit / Delete doctor
    # -----------------------------
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("### ➕ Add / ✏️ Edit / 🗑 Delete doctor")

    # select doctor to edit/delete (or choose Add new)
    doc_opts = ["Add new doctor"] + [f"{i}: {d.get('name')} ({d.get('username') or _normalize_username(d.get('name',''))})" for i, d in enumerate(doctors)]
    sel_doc = st.selectbox("Choose action / doctor", doc_opts, index=0, key="admin_doc_action")
    if sel_doc == "Add new doctor":
        with st.form("admin_add_doc", clear_on_submit=True):
            d_name = st.text_input("Name")
            d_specialty = st.text_input("Specialty")
            d_rating = st.number_input("Rating", min_value=0.0, max_value=5.0, value=4.5, step=0.1)
            d_slots = st.text_input("Slots (comma-separated) — e.g. 9:00 AM, 11:00 AM")
            d_username = st.text_input("Username (optional — autogenerated from name if blank)")
            add_sub = st.form_submit_button("Add Doctor")
        if add_sub:
            if not d_name.strip() or not d_specialty.strip():
                st.error("Name and Specialty required.")
            else:
                uname = d_username.strip() or _normalize_username(d_name)
                new_doc = {"name": d_name.strip(), "specialty": d_specialty.strip(), "rating": float(d_rating), "slots": [s.strip() for s in d_slots.split(",") if s.strip()], "username": uname}
                try:
                    doctors.append(new_doc)
                    with open("doctors.json", "w", encoding="utf-8") as f:
                        json.dump(doctors, f, ensure_ascii=False, indent=2)
                    doctors_df = pd.DataFrame(doctors)
                    users[uname] = {"password": "doctor_pass", "role": "Doctor", "display_name": d_name.strip()}
                    # refresh helpers
                    doctor_usernames = sorted([u for u, meta in users.items() if meta.get("role") == "Doctor"], key=lambda s: str(s).lower())
                    doctor_rows = [{"username": u, "name": users[u].get("display_name", u)} for u in doctor_usernames]
                    _display_to_uname.clear()
                    for u in doctor_usernames:
                        disp = users[u].get("display_name", u)
                        _display_to_uname["".join(ch for ch in str(disp).lower() if ch.isalnum())] = u
                    st.success(f"Doctor {d_name} added (username: {uname}).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add doctor: {e}")
    else:
        idx = int(sel_doc.split(":", 1)[0])
        doc = doctors[idx]
        cur_name = doc.get("name", "")
        cur_spec = doc.get("specialty", "")
        cur_rating = float(doc.get("rating", 4.5)) if doc.get("rating") is not None else 4.5
        cur_slots = ", ".join(doc.get("slots", [])) if isinstance(doc.get("slots", []), list) else str(doc.get("slots", ""))
        cur_uname = doc.get("username") or _normalize_username(cur_name)

        with st.form(f"admin_edit_doc_{idx}", clear_on_submit=False):
            e_name = st.text_input("Name", value=cur_name)
            e_specialty = st.text_input("Specialty", value=cur_spec)
            e_rating = st.number_input("Rating", min_value=0.0, max_value=5.0, value=cur_rating, step=0.1)
            e_slots = st.text_input("Slots (comma-separated)", value=cur_slots)
            e_username = st.text_input("Username", value=cur_uname)
            save_edit = st.form_submit_button("Save changes")
            delete_doc = st.form_submit_button("Delete this doctor")
        if save_edit:
            try:
                doctors[idx]["name"] = e_name.strip()
                doctors[idx]["specialty"] = e_specialty.strip()
                doctors[idx]["rating"] = float(e_rating)
                doctors[idx]["slots"] = [s.strip() for s in e_slots.split(",") if s.strip()]
                doctors[idx]["username"] = e_username.strip() or _normalize_username(e_name)
                with open("doctors.json", "w", encoding="utf-8") as f:
                    json.dump(doctors, f, ensure_ascii=False, indent=2)
                users[e_username.strip()] = {"password": users.get(cur_uname, {}).get("password", "doctor_pass"), "role": "Doctor", "display_name": e_name.strip()}
                if cur_uname != e_username.strip():
                    users.pop(cur_uname, None)
                doctors_df = pd.DataFrame(doctors)
                doctor_usernames = sorted([u for u, meta in users.items() if meta.get("role") == "Doctor"], key=lambda s: str(s).lower())
                doctor_rows = [{"username": u, "name": users[u].get("display_name", u)} for u in doctor_usernames]
                _display_to_uname.clear()
                for u in doctor_usernames:
                    disp = users[u].get("display_name", u)
                    _display_to_uname["".join(ch for ch in str(disp).lower() if ch.isalnum())] = u
                st.success("Doctor updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save changes: {e}")
        if delete_doc:
            try:
                removed = doctors.pop(idx)
                with open("doctors.json", "w", encoding="utf-8") as f:
                    json.dump(doctors, f, ensure_ascii=False, indent=2)
                users.pop(cur_uname, None)
                appts = load_appointments()
                kept = [a for a in appts if a.get("doctor_username") != cur_uname]
                save_appointments(kept)
                doctors_df = pd.DataFrame(doctors)
                doctor_usernames = sorted([u for u, meta in users.items() if meta.get("role") == "Doctor"], key=lambda s: str(s).lower())
                doctor_rows = [{"username": u, "name": users[u].get("display_name", u)} for u in doctor_usernames]
                _display_to_uname.clear()
                for u in doctor_usernames:
                    disp = users[u].get("display_name", u)
                    _display_to_uname["".join(ch for ch in str(disp).lower() if ch.isalnum())] = u
                st.success(f"Deleted doctor {removed.get('name')} and related appointments.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete doctor: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Doctors overview
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("### 👨‍⚕ All Doctors Overview")
    if not doctors_df.empty:
        # use dataframe to allow horizontal expansion under admin width
        st.dataframe(doctors_df, use_container_width=True)
    else:
        st.write("No doctors data available.")
    st.markdown("</div>", unsafe_allow_html=True)
