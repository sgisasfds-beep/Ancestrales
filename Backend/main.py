import os
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client
import google.generativeai as genai
from dotenv import load_dotenv

# Carga variables de entorno local si existe un archivo .env
load_dotenv()

app = FastAPI(title="Chocolates Ancestrales API")

# --- CONFIGURACIÓN DE CORS ---
# Permite que tu tienda.html se comunique con este servidor en Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, puedes cambiar "*" por tu dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Estas variables deben estar configuradas en el panel de Render
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WOMPI_INTEGRITY_SECRET = os.getenv("WOMPI_INTEGRITY_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicialización de clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- MODELOS DE DATOS ---
class ChatRequest(BaseModel):
    pregunta: str

class SignatureRequest(BaseModel):
    reference: str
    amount_in_cents: int
    currency: str = "COP"

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"message": "Servidor Ancestral Activo"}

@app.post("/generate-signature")
async def generate_signature(req: SignatureRequest):
    """
    Genera la firma de integridad SHA-256 requerida por Wompi.
    """
    try:
        # Cadena de integridad: referencia + monto + moneda + secreto
        chain = f"{req.reference}{req.amount_in_cents}{req.currency}{WOMPI_INTEGRITY_SECRET}"
        signature = hashlib.sha256(chain.encode()).hexdigest()
        return {"signature": signature}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sommelier")
async def sommelier_ia(req: ChatRequest):
    """
    Asesor profesional que utiliza datos de Supabase para responder.
    """
    try:
        # 1. Obtener catálogo actualizado de Supabase
        productos_db = supabase.table("productos").select("*").execute()
        
        # 2. PROMPT PROFESIONAL Y DIRECTO (HUMANO)
        contexto = """
        Eres un Asesor Especialista de la tienda Chocolates Ancestrales. 
        Tu tono es profesional, servicial y humano. Habla como un experto que atiende una boutique de lujo: con respeto pero de forma natural.

        REGLAS DE INTERACCIÓN:
        1. Responde de forma clara, directa y sin excesos poéticos.
        2. Usa los datos del catálogo para dar argumentos lógicos sobre sabor, energía o preparación.
        3. Justifica tus recomendaciones según la necesidad del cliente (ej. desayuno, regalo, amargor).
        4. Mantén las respuestas útiles y breves (máximo 3 frases).

        PRODUCTOS DISPONIBLES:
        """
        
        for p in productos_db.data:
            contexto += f"- {p['nombre']}: {p['perfil_sensorial']}. Maridaje: {p['maridaje_clave']}. Precio: ${p['precio_cop']} COP.\n"
        
        # 3. Configuración del modelo para respuestas consistentes
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash', # 👈 Este es el nombre actualizado
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 150,
            }
        )
        
        prompt_final = f"{contexto}\n\nCliente: {req.pregunta}\nAsesor:"
        response = model.generate_content(prompt_final)
        
        return {"respuesta": response.text}
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="El servicio de asesoría no está disponible en este momento.")

@app.post("/webhook-wompi")
async def webhook_wompi(data: dict):
    """
    Recibe la confirmación de pago de Wompi para futuros procesos.
    """
    print(f"Evento recibido de Wompi: {data}")
    return {"status": "ok"}