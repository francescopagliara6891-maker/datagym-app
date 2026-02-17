import streamlit as st
import warnings
import os

# --- 0. SOPPRESSIONE AVVISI (CLEAN CONSOLE) ---
warnings.filterwarnings("ignore")
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

from streamlit_option_menu import option_menu
from streamlit_ace import st_ace
import pandas as pd
from modules import auth
import time
from dotenv import load_dotenv
from supabase import create_client
import sys
from io import StringIO
import contextlib
import sqlite3
import google.generativeai as genai

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="DataGym", page_icon="⚡", layout="wide")
load_dotenv()

# Client Supabase
@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key) if url and key else None

supabase = init_supabase()

# AI Mentor Config
try:
    ai_key = os.getenv("GOOGLE_API_KEY")
    if ai_key:
        genai.configure(api_key=ai_key)
        ai_mentor = genai.GenerativeModel('gemini-2.0-flash')
    else:
        ai_mentor = None
except:
    ai_mentor = None

# Session State Init
if 'page' not in st.session_state: st.session_state['page'] = 'Home'
if 'user' not in st.session_state: st.session_state['user'] = None
if 'username' not in st.session_state: st.session_state['username'] = "Ospite"
if 'track' not in st.session_state: st.session_state['track'] = 'SQL'
if 'difficulty' not in st.session_state: st.session_state['difficulty'] = 'Principiante'
if 'custom_df' not in st.session_state: st.session_state['custom_df'] = None 
if 'custom_table_name' not in st.session_state: st.session_state['custom_table_name'] = None
if 'last_uploaded_file' not in st.session_state: st.session_state['last_uploaded_file'] = None 

# --- 3. CSS (DESIGN PRO) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #00D4FF !important; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { border: 1px solid #00D4FF; color: #00D4FF; background: transparent; border-radius: 5px; width: 100%; }
    .stButton>button:hover { background: #00D4FF; color: black; }
    .path-card { padding: 20px; border: 1px solid #333; border-radius: 10px; background: #1E1E1E; text-align: center; height: 100%; }
    .path-card h3 { font-size: 1.5rem; margin-bottom: 10px; color: #00D4FF; }
    .path-card p { color: #ccc; font-size: 1rem; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background: #0E1117; color: #666; text-align: center; padding: 10px; border-top: 1px solid #333; font-size: 0.8rem; z-index: 999; }
    .social-div { text-align: center; margin-top: 20px; }
    .social-div a { text-decoration: none; padding: 8px 15px; border-radius: 5px; color: white; margin: 0 5px; font-size: 0.9rem; border: 1px solid #444; }
    .linkedin { background-color: #0077b5; }
    .whatsapp { background-color: #25D366; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI ---
def get_lessons_from_db(track, difficulty):
    if not supabase: return {}
    try:
        response = supabase.table("lezioni").select("*").eq("track", track).eq("livello", difficulty).order("codice_lezione").execute()
        return {f"{r['codice_lezione']} - {r['titolo']}": r for r in response.data}
    except: return {}

def execute_python_code(code):
    output_capture = StringIO()
    try:
        with contextlib.redirect_stdout(output_capture):
            exec(code, {}, {})
        return output_capture.getvalue(), None
    except Exception as e: return None, str(e)

def run_query_on_csv(query, df, table_name):
    try:
        conn = sqlite3.connect(":memory:")
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        return pd.read_sql_query(query, conn), None
    except Exception as e: return None, str(e)

def get_ai_hint(user_code, task_desc, columns):
    if not ai_mentor: return "⚠️ Configura API Key."
    try:
        prompt = f"Sei un tutor SQL esperto. Task: '{task_desc}'. Colonne tabella: {columns}. Codice utente: '{user_code}'. Spiega brevemente l'errore o dai un consiglio teorico. NON scrivere la query corretta."
        response = ai_mentor.generate_content(prompt)
        return response.text
    except: return "Mentor occupato."

def share_buttons():
    url = "https://datagym.streamlit.app"
    st.markdown(f"""
    <div class="social-div">
        <p>📢 <b>Invita amici o condividi i tuoi risultati:</b></p>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" class="linkedin">Condividi su LinkedIn</a>
        <a href="https://wa.me/?text=Sto imparando Data Management su DataGym! 🚀 {url}" target="_blank" class="whatsapp">Invia su WhatsApp</a>
    </div>
    """, unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚡ DataGym")
    
    if st.session_state['user']:
        st.success(f"👤 {st.session_state['username']}")
        if st.button("Esci (Logout)"):
            auth.logout(); st.session_state['user'] = None; st.session_state['page'] = 'Home'; st.rerun()
    else:
        st.info("Ospite")
        if st.button("Accedi / Registrati"): st.session_state['page'] = 'Auth'; st.rerun()

    st.markdown("---")
    menu_options = ["Home", "DevLab", "Profilo"]
    try: curr_ix = menu_options.index(st.session_state['page'])
    except: curr_ix = 0
    selected = option_menu(None, menu_options, icons=['house', 'code-slash', 'person'], default_index=curr_ix, styles={"nav-link-selected": {"background-color": "#00D4FF", "color": "black"}})
    
    if selected != st.session_state['page']:
        if not (st.session_state['page'] == 'Auth' and selected == 'Home'):
            st.session_state['page'] = selected; st.rerun()
            
    st.markdown("---")
    st.link_button("✨ Chiedi Dati all'AI", "https://gemini.google.com/app", use_container_width=True)

# --- 6. ROUTING ---

# AUTH
if st.session_state['page'] == 'Auth':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("🔐 Accesso Lab")
        tab_log, tab_reg = st.tabs(["Login", "Registrati"])
        with tab_log:
            e = st.text_input("Email"); p = st.text_input("Password", type="password")
            if st.button("Entra", use_container_width=True):
                u, err = auth.sign_in(e, p)
                if u: st.session_state['user']=u; st.session_state['page']='Home'; st.rerun()
                else: st.error(err)
        with tab_reg:
            nu = st.text_input("Username"); ne = st.text_input("Email Reg"); np = st.text_input("Pass Reg", type="password")
            if st.button("Crea Account", use_container_width=True):
                u, err = auth.sign_up(ne, np, nu)
                if u: st.success("Creato! Accedi."); st.balloons()
                else: st.error(err)

# HOME
elif st.session_state['page'] == 'Home':
    st.title("DataGym_")
    st.markdown("### > The Interactive Learning Environment")
    st.markdown("""
    **Piattaforma avanzata per lo studio e la simulazione tecnica.**
    
    Progettata per studenti e professionisti, DataGym offre un ambiente reale per esercitarsi su:
    * **Data Management:** Interrogazione e manipolazione database (SQL).
    * **Business Intelligence:** Analisi e pulizia dati (Python/Pandas).
    
    *Preparati per i colloqui tecnici o affina le tue skill scrivendo codice che viene eseguito nel Cloud.*
    """)
    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""<div class="path-card"><h3>🗄️ SQL Track</h3><p>Database Postgres Reale in Cloud.<br>Dalle SELECT base alle Window Functions.</p></div>""", unsafe_allow_html=True)
        st.write("")
        if st.button("Avvia SQL Lab"): st.session_state['track']='SQL'; st.session_state['page']='DevLab'; st.rerun()
    with c2:
        st.markdown("""<div class="path-card"><h3>🐍 Python Track</h3><p>Analisi Dati con Pandas & Numpy.<br>Data Cleaning e Automazione.</p></div>""", unsafe_allow_html=True)
        st.write("")
        if st.button("Avvia Python Lab"): st.session_state['track']='PYTHON'; st.session_state['page']='DevLab'; st.rerun()
    st.write("---"); share_buttons()

# DEVLAB
elif st.session_state['page'] == 'DevLab':
    track = st.session_state['track']
    
    # 1. DASHBOARD DATI PERSISTENTE
    if st.session_state['custom_df'] is not None:
        with st.container():
            c_dash, c_btn = st.columns([6, 1])
            with c_dash:
                st.markdown(f"### 📊 Dati Attivi: `{st.session_state['custom_table_name']}`")
            with c_btn:
                # TASTO RESET DATI
                if st.button("🗑️ Reset", help="Rimuovi la tabella corrente"):
                    st.session_state['custom_df'] = None
                    st.session_state['custom_table_name'] = None
                    st.session_state['last_uploaded_file'] = None
                    st.rerun()
            
            st.dataframe(st.session_state['custom_df'].head(8), use_container_width=True, height=150)
            st.caption(f"Colonne: {', '.join(list(st.session_state['custom_df'].columns))}")
            st.divider()

    # 2. CONFIGURAZIONE
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: st.markdown(f"## 🛠️ Lab: **{track}**")
    with c2:
        diff = st.selectbox("Livello", ["Principiante", "Intermedio", "Avanzato"], index=["Principiante", "Intermedio", "Avanzato"].index(st.session_state['difficulty']), label_visibility="collapsed")
        if diff != st.session_state['difficulty']: st.session_state['difficulty']=diff; st.rerun()
    with c3:
        if st.session_state['user']: st.button("💾 Salva XP", use_container_width=True)
        else: st.caption("🔒 Login per salvare")

    # 3. DATA MANAGER
    with st.expander("📂 Carica i tuoi Dati (CSV)", expanded=False if st.session_state['custom_df'] is not None else True):
        st.info("💡 Usa il tasto nella barra laterale per generare un CSV con l'AI, poi caricalo qui.")
        up_file = st.file_uploader("Trascina il tuo file qui", type=['csv', 'xlsx'])
        
        if up_file:
            if st.session_state['last_uploaded_file'] != up_file.name:
                try:
                    up_file.seek(0)
                    df = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    tn = up_file.name.split('.')[0].replace(" ", "_").lower()
                    
                    st.session_state['custom_df'] = df
                    st.session_state['custom_table_name'] = tn
                    st.session_state['last_uploaded_file'] = up_file.name
                    
                    st.success(f"Caricato: {tn}")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e: st.error(f"Errore file: {e}")

    # 4. AREA LAVORO
    col_t, col_e = st.columns([1, 1.8], gap="medium")
    with col_t:
        st.markdown("### 📚 Syllabus")
        lezioni = get_lessons_from_db(track, st.session_state['difficulty'])
        if lezioni:
            scelta = st.selectbox("Esercizio:", list(lezioni.keys()))
            dati = lezioni[scelta]
            st.markdown(f"#### {dati['titolo']}")
            st.markdown(dati['teoria'])
            st.info(f"**TASK:** {dati['task']}")
            
            if st.button("🧠 Chiedi aiuto al Mentor", use_container_width=True):
                cols = str(list(st.session_state['custom_df'].columns)) if st.session_state['custom_df'] is not None else "Nessuna"
                hint = get_ai_hint("Analisi...", dati['task'], cols)
                st.warning(f"💡 **Mentor:** {hint}")

            with st.expander("🔍 Sintassi Generica"):
                st.code(dati['soluzione'], language=track.lower())
        else: st.warning("Lezioni non trovate.")

    with col_e:
        st.markdown("### ⚡ Terminale")
        ph = "-- Scrivi SQL..." if track == 'SQL' else "# Scrivi Python..."
        if st.session_state['custom_df'] is not None and track == 'SQL':
            ph = f"-- Esempio:\nSELECT * FROM {st.session_state['custom_table_name']} LIMIT 5;"
        
        code = st_ace(value="", placeholder=ph, language=track.lower(), theme="monokai", height=400)
        
        if st.button("▶️ RUN", type="primary", use_container_width=True):
            st.markdown("### Output")
            if track == 'SQL' and st.session_state['custom_df'] is not None:
                res, err = run_query_on_csv(code, st.session_state['custom_df'], st.session_state['custom_table_name'])
                if err: st.error(f"SQL Error: {err}")
                else: 
                    # GAMIFICATION: PALLONCINI SU SUCCESSO!
                    st.balloons()
                    st.success("✅ Query Eseguita con Successo!")
                    st.dataframe(res, use_container_width=True)
            elif track == 'PYTHON':
                out, err = execute_python_code(code)
                if err: st.error(err)
                else: 
                    st.balloons()
                    st.code(out) if out else st.success("Eseguito")
            else: st.warning("⚠️ Carica un file per attivare il Lab!")

elif st.session_state['page'] == 'Profilo':
    st.header("Profilo Studente"); st.write(f"Utente: **{st.session_state['username']}**"); share_buttons()

st.markdown('<div class="footer">Francesco Pagliara | Data Management & BI Research Project</div>', unsafe_allow_html=True)