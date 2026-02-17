import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Inizializzazione Client Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Controllo sicurezza
if not url or not key:
    raise ValueError("⚠️ Manca SUPABASE_URL o SUPABASE_KEY nel file .env")

supabase: Client = create_client(url, key)

def sign_in(email, password):
    """Login professionale tramite Supabase Auth"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        # Restituisce l'oggetto User e Session
        return response.user, None
    except Exception as e:
        return None, str(e)

def sign_up(email, password, username):
    """Registrazione con salvataggio metadati"""
    try:
        # 1. Crea utente nel sistema Auth (Gestione Password sicura)
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"username": username} # Salviamo lo username nei metadati
            }
        })
        
        # 2. Se l'auth va a buon fine, Supabase crea l'utente.
        # Nota: Idealmente dovremmo usare un 'Trigger' su Supabase per copiare l'utente
        # nella nostra tabella 'utenti', ma per ora lo facciamo via codice per semplicità.
        if auth_response.user:
            user_id = auth_response.user.id
            # Inseriamo nel nostro DB relazionale per le statistiche
            # Usiamo la libreria supabase per fare l'insert, non SQL grezzo!
            data = {
                "username": username,
                "email": email,
                "auth_user_id": user_id, # Colleghiamo le due identità
                "livello_xp": 1
            }
            supabase.table("utenti_app").insert(data).execute()
            
        return auth_response.user, None
    except Exception as e:
        return None, str(e)

def reset_password_request(email):
    """Invia email per il reset password"""
    try:
        supabase.auth.reset_password_email(email)
        return True, "Email di reset inviata! Controlla la posta."
    except Exception as e:
        return False, str(e)

def logout():
    """Chiude la sessione sicura"""
    supabase.auth.sign_out()