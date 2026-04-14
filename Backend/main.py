import os
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from supabase import create_client, Client
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carga variables de entorno
load_dotenv()

app = FastAPI(title="Chocolates Ancestrales API")

# --- CONFIGURACIÓN DE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE SEGURIDAD ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WOMPI_INTEGRITY_SECRET = os.getenv("WOMPI_INTEGRITY_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicialización de clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

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

@app.post("/sommelier")
async def sommelier_ia(req: ChatRequest):
    """
    Asesor profesional que utiliza el modelo Gemini 3 Flash Preview.
    """
    try:
        # 1. Obtener catálogo de productos
        productos_db = supabase.table("productos").select("*").execute()
        
        # 2. Instrucciones del sistema para el modelo
        instrucciones_sistema = """
        Eres un Asesor Especialista de la tienda Chocolates Ancestrales. 
        Tu tono es profesional, servicial y humano.
        
        REGLAS:
        1. Respuestas breves y directas (máximo 3 frases).
        2. Usa únicamente los datos del catálogo proporcionado.
        3. Justifica tus sugerencias según el perfil sensorial o maridaje.

        PRODUCTOS DISPONIBLES EN TIENDA:
        """
        for p in productos_db.data:
            instrucciones_sistema += f"- {p['nombre']}: {p['perfil_sensorial']}. Maridaje: {p['maridaje_clave']}. Precio: ${p['precio_cop']} COP.\n"

        # 3. Generación de respuesta (Modelo verificado por tu diagnóstico)
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            config=types.GenerateContentConfig(
                system_instruction=instrucciones_sistema,
                temperature=1.0,
                max_output_tokens=150,
            ),
            contents=req.pregunta
        )
        
        return {"respuesta": response.text}
        
    except Exception as e:
        print(f"Error en endpoint /sommelier: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en el servicio de asesoría.")

@app.post("/generate-signature")
async def generate_signature(req: SignatureRequest):
    """
    Genera la firma de integridad para Wompi.
    """
    try:
        chain = f"{req.reference}{req.amount_in_cents}{req.currency}{WOMPI_INTEGRITY_SECRET}"
        signature = hashlib.sha256(chain.encode()).hexdigest()
        return {"signature": signature}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook-wompi")
async def webhook_wompi(data: dict):
    print(f"Evento de Wompi: {data}")
    return {"status": "ok"}