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
        
        # 1. Instrucción más específica para evitar diagnósticos médicos
        instrucciones_sistema = """
        Eres 'El Sommelier', un experto en cacao de origen y maestro en maridaje de la tienda 'Chocolates Ancestrales'. 
        Tu misión es guiar al usuario a través de una experiencia sensorial mística y profesional.

        TONO Y ESTILO:
        - Elegante, culto y ligeramente evocador (usa términos como 'notas', 'postgusto', 'terroir', 'ancestral').
        - Sé humano y cálido, pero mantén la brevedad (máximo 3-4 frases).
        - Usa **negritas** para resaltar los nombres de los productos y características clave.

        REGLAS DE ORO:
        1. CONSEJO MÉDICO: Si preguntan por salud (ej. diabetes, hipertensión), aclara brevemente que no eres médico, pero recomienda opciones con **alto porcentaje de cacao (70%+)** o **sin azúcares añadidos** basándote en el catálogo.
        2. EXCLUSIVIDAD: Si un producto no está en la lista de abajo, di que "no forma parte de nuestra cava actual" y sugiere el más parecido.
        3. MARIDAJE: Siempre justifica tu elección mencionando una nota de sabor y un acompañamiento.

        CATÁLOGO DE PRODUCTOS DISPONIBLES:
        """
        # Aquí sigue tu bucle for para inyectar los productos de Supabase
        for p in productos_db.data:
            instrucciones_sistema += f"- **{p['nombre']}**: Perfil: {p['perfil_sensorial']}. Maridaje ideal: {p['maridaje_clave']}. Precio: ${p['precio_cop']} COP.\n"

        # 2. Configuración ajustada
        config = types.GenerateContentConfig(
            system_instruction=instrucciones_sistema,
            temperature=0.7, # Más estable
            max_output_tokens=200,
            # Esto ayuda a que el modelo no se bloquee tan agresivamente en respuestas informativas
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_LOW_AND_ABOVE",
                ),
            ]
        )

        response = client.models.generate_content(
            model="gemini-1.5-flash", # Te sugiero usar la versión estable
            config=config,
            contents=req.pregunta
        )
        
        # 3. Verificación de seguridad
        if not response.text:
            return {"respuesta": "Como sommelier, prefiero recomendarte chocolates basados en su sabor. Para temas de salud, te sugiero consultar a un especialista."}

        return {"respuesta": response.text}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"respuesta": "Mi cava de conocimientos está cerrada un momento. ¿Podrías preguntar de nuevo?"}

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