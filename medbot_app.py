# medbot_app.py
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
.chat-wrapper { max-width: 1100px; margin: 0 auto; }
.user-bubble { background:#DCF8C6; padding:12px; border-radius:12px; display:inline-block; margin:6px 0; color:#000; max-width:80%; }
.bot-bubble { background:#F1F1F1; padding:12px; border-radius:12px; display:inline-block; margin:6px 0; color:#000; max-width:80%; }
.meta { font-size:0.8rem; color:#444; margin-bottom:6px; font-weight:600; }
.header-space { margin-top:10px; margin-bottom:10px; }
.app-card { background: #ffffff; border-radius:10px; padding:12px; box-shadow: 0 1px 6px rgba(0,0,0,0.08); margin-bottom:14px; }
.status-pill { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:600; }
.status-pending { background:#FFF3CD; color:#856404; }
.status-accepted { background:#D4EDDA; color:#155724; }
.status-rejected { background:#F8D7DA; color:#721C24; }
.small-muted { font-size:0.85rem; color:#666; }
</style>
"""
st.markdown(CHAT_CSS, unsafe_allow_html=True)

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
    try:
        vec = vectorizer.transform([user_input.lower()])
        prediction = model.predict(vec)
        predicted_tag = le.inverse_transform(prediction)[0] if hasattr(le, "inverse_transform") else prediction[0]
    except Exception:
        predicted_tag = None

    if predicted_tag:
        for intent in intents.get('intents', []):
            if intent.get('tag') == predicted_tag:
                resp_choices = intent.get('responses', [])
                response = random.choice(resp_choices) if resp_choices else "Sorry, I don't understand."
                fups = None
                if predicted_tag in follow_ups:
                    fups = follow_ups[predicted_tag]
                elif intent.get('follow_up_questions'):
                    fups = intent.get('follow_up_questions')
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
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'current_symptom' not in st.session_state: st.session_state.current_symptom = None
if 'follow_up_questions' not in st.session_state: st.session_state.follow_up_questions = []
if 'follow_up_index' not in st.session_state: st.session_state.follow_up_index = 0
if 'follow_up_answers' not in st.session_state: st.session_state.follow_up_answers = {}
if 'asking_follow_up' not in st.session_state: st.session_state.asking_follow_up = False
if 'symptoms_collected' not in st.session_state: st.session_state.symptoms_collected = []
if 'appointments' not in st.session_state: st.session_state.appointments = load_appointments()

# -----------------------------
# UI helpers: chat bubbles (escape input)
# -----------------------------
def _render_user_bubble(text):
    if text is None:
        return
    safe = html.escape(str(text)).replace("\n", "<br>")
    st.markdown(f"<div style='text-align:right'><div class='user-bubble'><div class='meta'>You</div>{safe}</div></div>", unsafe_allow_html=True)

def _render_bot_bubble(text):
    if text is None:
        return
    safe = html.escape(str(text)).replace("\n", "<br>")
    st.markdown(f"<div style='text-align:left'><div class='bot-bubble'><div class='meta'>MedBot</div>{safe}</div></div>", unsafe_allow_html=True)

# -----------------------------
# UI: Header / Login
# -----------------------------
st.markdown("<div class='header-space'></div>", unsafe_allow_html=True)
st.title("🩺 MedBot Healthcare Assistant")

if not st.session_state.logged_in:
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
            username_input = st.text_input("Username (doctors: choose name above or type username)")
        password = st.text_input("Password", type="password")
    if user_type == "Doctor" and doctor_rows:
        st.info("Choose your name from the dropdown to avoid typing the username. Demo doctors use password 'doctor_pass'.")

    # Login handler
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
else:
    st.sidebar.success(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# -----------------------------
# PATIENT DASHBOARD
# -----------------------------
if st.session_state.logged_in and st.session_state.role == "Patient":
    st.subheader(f"Welcome, {st.session_state.username}!")
    col_chat, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("<div class='app-card'>", unsafe_allow_html=True)
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

        if st.button("Clear Chat", key="clear_chat_main"):
            st.session_state.chat_history = []
            st.session_state.current_symptom = None
            st.session_state.asking_follow_up = False
            st.session_state.follow_up_index = 0
            st.session_state.follow_up_answers = {}
            st.session_state.symptoms_collected = []
            st.rerun()

    with col_chat:
        st.markdown("### 💬 Chat with MedBot")
        # render history
        for chat in st.session_state.chat_history:
            if chat.get("user"):
                _render_user_bubble(chat['user'])
            if chat.get("bot"):
                _render_bot_bubble(chat['bot'])

        # follow-up handling
        if st.session_state.asking_follow_up:
            idx = st.session_state.follow_up_index
            fqs = st.session_state.follow_up_questions or []
            if idx < len(fqs):
                current_q = fqs[idx]
                # ensure bot question present once
                if not any(chat.get("bot") == current_q for chat in st.session_state.chat_history):
                    st.session_state.chat_history.append({"user": None, "bot": current_q})
                ans = st.text_input(current_q, key=f"fup_{idx}")
                if st.button("Answer", key=f"ans_btn_{idx}") and ans.strip():
                    st.session_state.chat_history.append({"user": ans.strip(), "bot": None})
                    st.session_state.follow_up_answers[current_q] = ans.strip()
                    st.session_state.follow_up_index += 1
                    if st.session_state.follow_up_index < len(fqs):
                        next_q = fqs[st.session_state.follow_up_index]
                        if not any(chat.get("bot") == next_q for chat in st.session_state.chat_history):
                            st.session_state.chat_history.append({"user": None, "bot": next_q})
                    else:
                        # finalize
                        st.session_state.asking_follow_up = False
                        symptom = st.session_state.current_symptom or " / ".join(st.session_state.follow_up_answers.values())
                        username_display = st.session_state.username or "User"
                        bot_msg = (f"Thank you, {username_display}. Based on what you’ve shared, "
                                   f"it seems you’re experiencing symptoms related to {symptom}. "
                                   "Here are some doctors who can help you.")
                        st.session_state.chat_history.append({"user": None, "bot": bot_msg})
                        st.session_state.symptoms_collected.append(symptom)
                        st.session_state.follow_up_questions = []
                        st.session_state.follow_up_index = 0
                        st.session_state.follow_up_answers = {}
            else:
                st.session_state.asking_follow_up = False

        else:
            if not st.session_state.symptoms_collected:
                user_input = st.text_input("Describe your symptom (e.g., 'I have a fever')", key="symptom_input")
                if st.button("Send", key="send_symptom") and user_input.strip():
                    with st.spinner("MedBot is thinking..."):
                        time.sleep(0.5)
                        bot_resp, predicted_tag, fups = get_bot_response(user_input)
                    st.session_state.chat_history.append({"user": user_input.strip(), "bot": bot_resp})
                    st.session_state.current_symptom = predicted_tag or user_input.strip()
                    if fups:
                        st.session_state.follow_up_questions = fups
                        st.session_state.follow_up_index = 0
                        st.session_state.follow_up_answers = {}
                        st.session_state.asking_follow_up = True
                        # append first follow-up once
                        first_q = fups[0] if fups else None
                        if first_q and not any(chat.get("bot") == first_q for chat in st.session_state.chat_history):
                            st.session_state.chat_history.append({"user": None, "bot": first_q})
                    else:
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
                        st.session_state.follow_up_questions = []
                        st.session_state.follow_up_index = 0
                        st.session_state.follow_up_answers = {}
                        st.session_state.asking_follow_up = False
                        st.rerun()
                else:
                    st.write("No doctors found for that symptom — try rephrasing.")

# -----------------------------
# DOCTOR DASHBOARD
# -----------------------------
elif st.session_state.logged_in and st.session_state.role == "Doctor":
    doc_uname = st.session_state.username
    display_name = users.get(doc_uname, {}).get("display_name")
    if not display_name and 'username' in doctors_df.columns:
        row = doctors_df.loc[doctors_df['username'] == doc_uname]
        if not row.empty:
            display_name = row.iloc[0].get('name')
    display_name = display_name or doc_uname

    st.subheader(f"Welcome, Dr. {display_name}!")
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("### 🗓 Your Appointments")
    appts = get_doctor_appointments(doc_uname) or []
    if appts:
        for i, a in enumerate(sorted(appts, key=lambda x: x.get("created_at") or "", reverse=True)):
            status = a.get("status", "Pending")
            pill_class = "status-pending"
            emoji = "⚪"
            if status == "Accepted":
                pill_class = "status-accepted"; emoji = "✅"
            elif status == "Rejected":
                pill_class = "status-rejected"; emoji = "❌"
            st.markdown("<div class='app-card'>", unsafe_allow_html=True)
            st.markdown(f"**Patient:** {a.get('patient')}  \n**Time:** {a.get('time')}  \n**Symptom:** {a.get('symptom')}")
            st.markdown(f"<div class='small-muted'>Created: {a.get('created_at')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='status-pill {pill_class}' style='margin-top:8px'>{emoji} {status}</div>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                if status == "Pending":
                    if st.button("Accept", key=f"accept_{a.get('patient')}_{a.get('time')}"):
                        ok = update_appointment_status(a.get('patient'), doc_uname, a.get('time'), "Accepted")
                        if ok:
                            st.success("Appointment accepted.")
                            st.rerun()
                        else:
                            st.error("Failed to update appointment.")
            with col2:
                if status == "Pending":
                    if st.button("Reject", key=f"reject_{a.get('patient')}_{a.get('time')}"):
                        ok = update_appointment_status(a.get('patient'), doc_uname, a.get('time'), "Rejected")
                        if ok:
                            st.warning("Appointment rejected.")
                            st.rerun()
                        else:
                            st.error("Failed to update appointment.")
            with col3:
                # allow doctor to delete this appointment (e.g., after treatment)
                if st.button("Delete appointment", key=f"doc_delete_{i}_{a.get('patient')}_{a.get('time')}"):
                    try:
                        appts_all = load_appointments()
                        removed = False
                        for j, ap in enumerate(appts_all):
                            if ap.get("patient") == a.get("patient") and ap.get("doctor_username") == doc_uname and ap.get("time") == a.get("time") and ap.get("created_at") == a.get("created_at"):
                                appts_all.pop(j)
                                removed = True
                                break
                        if removed:
                            save_appointments(appts_all)
                            st.success("Appointment deleted.")
                            st.rerun()
                        else:
                            st.error("Could not find appointment to delete.")
                    except Exception as e:
                        st.error(f"Failed to delete appointment: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        # bulk delete older than days control for doctor
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        days = st.number_input("Delete my appointments older than (days)", min_value=1, value=30, step=1, key="doc_delete_old_days")
        if st.button("Delete my older appointments", key="doc_delete_old"):
            cutoff = datetime.utcnow() - timedelta(days=int(days))
            appts_all = load_appointments()
            kept = []
            removed_count = 0
            for a in appts_all:
                if a.get("doctor_username") != doc_uname:
                    kept.append(a)
                    continue
                created = a.get("created_at")
                dt = None
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                    except Exception:
                        dt = None
                if dt and dt < cutoff:
                    removed_count += 1
                else:
                    kept.append(a)
            save_appointments(kept)
            st.success(f"Deleted {removed_count} of your appointment(s) older than {days} days.")
            st.rerun()
    else:
        st.write("No appointments found.")
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# ADMIN DASHBOARD (edit/delete doctor + manage appts)
# -----------------------------
elif st.session_state.logged_in and st.session_state.role == "Admin":
    st.subheader("Admin Dashboard")
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown("### 📋 All Appointments")
    all_appts = load_appointments()
    if all_appts:
        df = pd.DataFrame(all_appts)
        st.table(df)

        st.markdown("### Manage appointment")
        options = [f"{i}: {r.get('patient')} | {r.get('doctor') or r.get('doctor_username')} | {r.get('time')} | {r.get('status')}" for i, r in enumerate(all_appts)]
        sel = st.selectbox("Select appointment", ["Select"] + options, index=0)
        if sel and sel != "Select":
            idx = int(sel.split(":", 1)[0])
            row = all_appts[idx]
            st.markdown(f"**Selected:** {row.get('patient')} — {row.get('doctor') or row.get('doctor_username')} — {row.get('time')} — {row.get('status')}")
            col_a, col_b, col_c = st.columns([1,1,1])
            with col_a:
                new_status = st.selectbox("New status", ["Pending", "Accepted", "Rejected"], index=["Pending","Accepted","Rejected"].index(row.get("status","Pending")))
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
        st.table(doctors_df)
    else:
        st.write("No doctors data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# Fallback
else:
    st.info("Select a role and login to continue.")