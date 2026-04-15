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
    try:
        productos_db = supabase.table("productos").select("*").execute()
        
        instrucciones_sistema = """
        Eres 'El Sommelier', un experto en cacao de origen y maestro en maridaje de la tienda 'Chocolates Ancestrales'. 
        Tu misión es guiar al usuario a través de una experiencia sensorial mística y profesional.

        TONO Y ESTILO:
        - Elegante, culto y evocador.
        - Sé humano y cálido. 
        - Usa **negritas** para resaltar nombres de productos.

        REGLAS DE ORO:
        1. CONSEJO MÉDICO: Si preguntan por salud, aclara que no eres médico y recomienda opciones con 70%+ cacao.
        2. EXCLUSIVIDAD: Si un producto no está en la lista, sugiere el más parecido.
        3. MARIDAJE: Siempre justifica tu elección.
        
        CATÁLOGO:
        """
        for p in productos_db.data:
            instrucciones_sistema += f"- **{p['nombre']}**: Perfil: {p['perfil_sensorial']}. Maridaje: {p['maridaje_clave']}.\n"

        # CAMBIO CLAVE: Modelo actualizado y aumento de tokens
        config = types.GenerateContentConfig(
            system_instruction=instrucciones_sistema,
            temperature=0.7,
            max_output_tokens=1000,  # Aumentado de 200 a 1000 para evitar cortes
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_LOW_AND_ABOVE",
                ),
            ]
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash", # Usando el modelo de tu lista
            config=config,
            contents=req.pregunta
        )
        
        # MONITOR EN CONSOLA: Aquí verás si el modelo genera todo el texto
        if response.text:
            print("-" * 30)
            print(f"DEBUG - RESPUESTA COMPLETA:\n{response.text}")
            print("-" * 30)
            return {"respuesta": response.text}
        
        return {"respuesta": "Lo siento, mi paladar está confundido. ¿Podrías repetir?"}
        
    except Exception as e:
        print(f"Error crítico: {str(e)}")
        return {"respuesta": "Mi cava de conocimientos está cerrada un momento."}

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