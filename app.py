import streamlit as st
import warnings
import os

# --- 0. CONFIGURAZIONE AMBIENTE ---
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
import plotly.express as px

# --- 1. SETUP ---
st.set_page_config(page_title="DataGym", page_icon="⚡", layout="wide")
load_dotenv()

@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key) if url and key else None

supabase = init_supabase()

# Session State
if 'page' not in st.session_state: st.session_state['page'] = 'Home'
if 'user' not in st.session_state: st.session_state['user'] = None
if 'username' not in st.session_state: st.session_state['username'] = "Ospite"
if 'track' not in st.session_state: st.session_state['track'] = 'SQL'
if 'difficulty' not in st.session_state: st.session_state['difficulty'] = 'Principiante'
if 'custom_df' not in st.session_state: st.session_state['custom_df'] = None 
if 'custom_table_name' not in st.session_state: st.session_state['custom_table_name'] = None
if 'last_uploaded_file' not in st.session_state: st.session_state['last_uploaded_file'] = None 
if 'xp' not in st.session_state: st.session_state['xp'] = 0
if 'completed_tasks' not in st.session_state: st.session_state['completed_tasks'] = 0

# --- 2. CSS BLINDATO (FORCE DARK EVERYWHERE) ---
st.markdown("""
<style>
    /* Sfondo Globale */
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    
    /* Testi */
    h1, h2, h3, h4, h5, h6, p, span, div { color: #FAFAFA !important; font-family: 'Segoe UI', sans-serif; }
    h1, h2, h3 { color: #00D4FF !important; }
    
    /* Input Fields Scuro */
    .stTextInput > div > div > input {
        color: #FAFAFA !important;
        background-color: #1E1E1E !important;
        border-color: #333 !important;
    }
    
    /* Selectbox */
    div[data-baseweb="select"] > div {
        background-color: #1E1E1E !important;
        color: #FAFAFA !important;
        border-color: #333 !important;
    }
    
    /* File Uploader Scuro */
    [data-testid="stFileUploader"] {
        background-color: #1E1E1E !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #444;
    }
    [data-testid="stFileUploader"] section { background-color: #1E1E1E !important; }
    [data-testid="stFileUploader"] small { color: #AAA !important; }

    /* Bottoni */
    .stButton>button { 
        border: 1px solid #00D4FF !important; 
        color: #00D4FF !important; 
        background: transparent !important; 
        border-radius: 5px; 
        width: 100%; 
    }
    .stButton>button:hover { 
        background: #00D4FF !important; 
        color: black !important; 
    }
    
    /* Card Home */
    .path-card { 
        padding: 20px; 
        border: 1px solid #333; 
        border-radius: 10px; 
        background: #1E1E1E !important; 
        text-align: center; 
        height: 100%; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .path-card p { color: #ccc !important; }
    
    /* Footer */
    .footer { 
        position: fixed; left: 0; bottom: 0; width: 100%; 
        background: #0E1117 !important; color: #666 !important; 
        text-align: center; padding: 10px; font-size: 0.8rem; z-index: 999; 
        border-top: 1px solid #333;
    }
    
    /* Stat Box */
    .stat-box { 
        background-color: #1E1E1E !important; 
        padding: 15px; border-radius: 10px; 
        text-align: center; border: 1px solid #333; 
    }
    .stat-number { font-size: 2rem; font-weight: bold; color: #00D4FF !important; }
    .stat-label { font-size: 0.9rem; color: #AAA !important; }
    
    /* Social Buttons */
    .social-div { text-align: center; margin-top: 20px; }
    .social-div a { 
        text-decoration: none; 
        padding: 10px 20px; 
        border-radius: 5px; 
        color: white !important; 
        margin: 0 10px; 
        font-size: 0.9rem; 
        font-weight: bold;
    }
    .linkedin { background-color: #0077b5; border: 1px solid #0077b5; }
    .whatsapp { background-color: #25D366; border: 1px solid #25D366; }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNZIONI ---
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

def update_xp():
    st.session_state['xp'] += 50
    st.session_state['completed_tasks'] += 1
    if st.session_state['user']:
        try:
            supabase.table("utenti_app").update({
                "xp": st.session_state['xp'],
                "completed_tasks": st.session_state['completed_tasks']
            }).eq("auth_user_id", st.session_state['user'].id).execute()
        except: pass
    st.toast("+50 XP! 🚀", icon="🔥")

def share_buttons():
    url = "https://datagym.streamlit.app"
    st.markdown(f"""
    <div class="social-div">
        <p style="color:#888; margin-bottom:15px;">📢 <b>Invita amici o condividi i tuoi risultati:</b></p>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" class="linkedin">Condividi su LinkedIn</a>
        <a href="https://wa.me/?text=Sto imparando Data Management su DataGym! 🚀 {url}" target="_blank" class="whatsapp">Invia su WhatsApp</a>
    </div>
    """, unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚡ DataGym")
    
    if st.session_state['user']:
        display_name = st.session_state['username']
        if display_name == "Ospite" and st.session_state['user'].email:
             display_name = st.session_state['user'].email.split("@")[0]
        
        st.success(f"👤 {display_name}")
        st.caption(f"Livello: {int(st.session_state['xp']/500)+1} | XP: {st.session_state['xp']}")
        
        if st.button("Esci (Logout)"):
            auth.logout(); st.session_state['user'] = None; st.session_state['username'] = "Ospite"; st.session_state['xp']=0; st.session_state['page'] = 'Home'; st.rerun()
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
    st.link_button("✨ Chat con AI (Gemini)", "https://gemini.google.com/app", use_container_width=True, help="Apri Gemini per generare dataset.")

# --- 5. ROUTING ---

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
                if u:
                    st.session_state['user'] = u
                    st.session_state['username'] = u.email.split("@")[0]
                    try:
                        d = supabase.table("utenti_app").select("*").eq("auth_user_id", u.id).execute()
                        if d.data: 
                            user_data = d.data[0]
                            st.session_state['username'] = user_data.get('username', u.email.split("@")[0])
                            st.session_state['xp'] = user_data.get('xp', 0)
                            st.session_state['completed_tasks'] = user_data.get('completed_tasks', 0)
                    except: pass
                    st.success("Accesso riuscito!"); time.sleep(0.5); st.session_state['page']='Home'; st.rerun()
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
        st.markdown("""
        <div class="path-card">
            <h3>🗄️ SQL Track</h3>
            <p>Database Postgres Reale in Cloud.<br>
            Dalle <code>SELECT</code> base alle <code>Window Functions</code>.<br>
            Esercitati su scenari di estrazione dati reali.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("Avvia SQL Lab"): st.session_state['track']='SQL'; st.session_state['page']='DevLab'; st.rerun()
            
    with c2:
        st.markdown("""
        <div class="path-card">
            <h3>🐍 Python Track</h3>
            <p>Analisi Dati con Pandas & Numpy.<br>
            Data Cleaning, Manipolazione e Automazione.<br>
            Ambiente Python sicuro per i tuoi script.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("Avvia Python Lab"): st.session_state['track']='PYTHON'; st.session_state['page']='DevLab'; st.rerun()

    st.write("---")
    share_buttons()

# DEVLAB
elif st.session_state['page'] == 'DevLab':
    track = st.session_state['track']
    
    # 1. DASHBOARD
    if st.session_state['custom_df'] is not None:
        with st.container():
            st.warning(f"👉 **Tabella attiva:** `{st.session_state['custom_table_name']}`")
            
            c_dash, c_btn = st.columns([6, 1])
            with c_dash: st.caption("Anteprima dati (prime 5 righe):")
            with c_btn:
                if st.button("🗑️ Reset"):
                    st.session_state['custom_df']=None; st.session_state['last_uploaded_file']=None; st.rerun()
            st.dataframe(st.session_state['custom_df'].head(5), use_container_width=True)
            st.divider()

    # 2. CONFIG
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: st.markdown(f"## 🛠️ Lab: **{track}**")
    with c2:
        diff = st.selectbox("Livello", ["Principiante", "Intermedio", "Avanzato"], index=["Principiante", "Intermedio", "Avanzato"].index(st.session_state['difficulty']), label_visibility="collapsed")
        if diff != st.session_state['difficulty']: st.session_state['difficulty']=diff; st.rerun()
    with c3:
        if st.session_state['user']: st.button("💾 Salva XP")
        else: st.caption("🔒 Login req.")

    # 3. UPLOAD
    with st.expander("📂 Carica CSV", expanded=False if st.session_state['custom_df'] is not None else True):
        st.info("Genera un CSV con l'AI e caricalo qui.")
        up_file = st.file_uploader("Upload", type=['csv', 'xlsx'])
        if up_file:
            if st.session_state['last_uploaded_file'] != up_file.name:
                try:
                    up_file.seek(0)
                    df = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    st.session_state['custom_df'] = df
                    tn = up_file.name.split('.')[0].replace(" ", "_").lower()
                    st.session_state['custom_table_name'] = tn
                    st.session_state['last_uploaded_file'] = up_file.name
                    st.success(f"Caricato! Tabella: {tn}"); time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"Errore: {e}")

    # 4. WORKSPACE
    col_t, col_e = st.columns([1, 1.8], gap="medium")
    with col_t:
        st.markdown("### 📚 Syllabus")
        lezioni = get_lessons_from_db(track, st.session_state['difficulty'])
        if lezioni:
            s = st.selectbox("Esercizio:", list(lezioni.keys()))
            d = lez = lezioni[s]
            st.markdown(f"#### {d['titolo']}\n{d['teoria']}")
            st.info(f"**TASK:** {d['task']}")
            with st.expander("🔍 Sintassi"): st.code(d['soluzione'], language=track.lower())
        else: st.warning("Lezioni non trovate.")

    with col_e:
        st.markdown("### ⚡ Terminale")
        ph = "-- Scrivi query..."
        if st.session_state['custom_df'] is not None and track == 'SQL':
            ph = f"SELECT * FROM {st.session_state['custom_table_name']} LIMIT 5;"
        
        code = st_ace(value="", placeholder=ph, language=track.lower(), theme="monokai", height=400)
        
        if st.button("▶️ RUN", type="primary", use_container_width=True):
            st.markdown("### Output")
            if track == 'SQL':
                if st.session_state['custom_df'] is not None:
                    res, err = run_query_on_csv(code, st.session_state['custom_df'], st.session_state['custom_table_name'])
                    if err: st.error(f"Errore SQL: {err}")
                    else: 
                        st.balloons(); update_xp()
                        st.success("✅ Query OK"); st.dataframe(res, use_container_width=True)
                else: st.warning("Carica un file!")
            else:
                out, err = execute_python_code(code)
                if err: st.error(err)
                else: 
                    st.balloons(); update_xp()
                    # FIX DEL DELTAGENERATOR: Niente istruzioni inline!
                    if out:
                        st.code(out)
                    else:
                        st.success("Codice eseguito con successo.")

# PROFILO
elif st.session_state['page'] == 'Profilo':
    st.header("Profilo Studente")
    if st.session_state['user']:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"### 👤 {st.session_state['username']}")
            st.caption(st.session_state['user'].email)
            st.success("Account Verificato")
            
            # GRAFICO RADAR
            base_val = min(st.session_state['xp'] / 100, 10)
            df_radar = pd.DataFrame(dict(
                r=[base_val, base_val*0.8, base_val*1.2, st.session_state['completed_tasks'], 5],
                theta=['SQL', 'Python', 'Data Mgmt', 'Esercizi', 'Costanza']
            ))
            fig = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
            fig.update_traces(fill='toself')
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 20])),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("### 🏆 Statistiche")
            k1, k2, k3 = st.columns(3)
            k1.markdown(f"<div class='stat-box'><div class='stat-number'>{st.session_state['xp']}</div><div class='stat-label'>XP</div></div>", unsafe_allow_html=True)
            k2.markdown(f"<div class='stat-box'><div class='stat-number'>{st.session_state['completed_tasks']}</div><div class='stat-label'>Task</div></div>", unsafe_allow_html=True)
            k3.markdown(f"<div class='stat-box'><div class='stat-number'>{int(st.session_state['xp']/500)+1}</div><div class='stat-label'>Lv</div></div>", unsafe_allow_html=True)
            st.write("")
            st.progress((st.session_state['xp'] % 500) / 500, text="Progresso Livello")
        
        st.write("---")
        share_buttons()
    else: st.warning("Accedi per vedere il tuo profilo.")

st.markdown('<div class="footer">Francesco Pagliara | Data Management & BI Research Project</div>', unsafe_allow_html=True)