import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import logging

# S'assurer que le dossier backend est dans le path de recherche
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from tools import outil_estimation_ml

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EstimIA-API")

app = FastAPI(
    title="EstimIA — API d'Estimation Immobiliere",
    description="API REST connectant le moteur d'apprentissage statistique RandomForest d'Ile-de-France et l'Agent IA.",
    version="1.0.0"
)

# Configuration du CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permet à Next.js frontend d'appeler l'API en local ou en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schémas de données Pydantic ---

class EstimationRequest(BaseModel):
    surface: float = Field(..., description="Surface habitable en m2", ge=10.0, le=300.0)
    pieces: int = Field(..., description="Nombre de pieces principales", ge=1, le=10)
    code_postal: str = Field(..., description="Code postal a 5 chiffres (ex: 92100)")
    type_bien: str = Field(..., description="Type de bien ('Maison' ou 'Appartement')")
    annee_visite: int = Field(2025, description="Annee de reference pour l'estimation", ge=2020, le=2030)

    @field_validator('code_postal')
    def validate_code_postal(cls, v):
        v_clean = str(v).strip()
        if len(v_clean) != 5 or not v_clean.isdigit():
            raise ValueError("Le code postal doit contenir exactement 5 chiffres.")
        if not (v_clean.startswith("75") or v_clean.startswith("77") or v_clean.startswith("78") or 
                v_clean.startswith("91") or v_clean.startswith("92") or v_clean.startswith("93") or 
                v_clean.startswith("94") or v_clean.startswith("95")):
            raise ValueError("Le code postal doit appartenir a la region Ile-de-France (75, 77, 78, 91-95).")
        return v_clean

    @field_validator('type_bien')
    def validate_type_bien(cls, v):
        v_clean = str(v).strip().capitalize()
        if v_clean not in ["Maison", "Appartement"]:
            raise ValueError("Le type de bien doit etre 'Maison' ou 'Appartement'.")
        return v_clean

class ChatRequest(BaseModel):
    message: str = Field(..., description="Le message ou la question de l'utilisateur")

# --- Routes API ---

@app.get("/")
def read_root():
    from tools import MODELE, LOOKUP_POSTAUX
    model_status = "Charge avec succes" if MODELE is not None else "Non disponible"
    cache_status = "Charge avec succes" if LOOKUP_POSTAUX is not None else "Non disponible"
    
    return {
        "status": "online",
        "service": "EstimIA Backend API",
        "version": "1.0.0",
        "configuration": {
            "modele_ml_idf": model_status,
            "cache_geographique_idf": cache_status,
            "departements_couverts": ["75", "77", "78", "91", "92", "93", "94", "95"]
        }
    }

@app.post("/estimate", status_code=status.HTTP_200_OK)
def estimate_property(req: EstimationRequest):
    logger.info(f"Estimation demandee : {req.type_bien}, {req.surface}m2, {req.pieces}p a {req.code_postal}")
    
    res = outil_estimation_ml(
        surface=req.surface,
        pieces=req.pieces,
        code_postal=req.code_postal,
        type_bien=req.type_bien,
        annee_visite=req.annee_visite,
        return_dict=True
    )
    
    if "erreur" in res:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res["erreur"]
        )
        
    return res

@app.post("/agent/chat", status_code=status.HTTP_200_OK)
def agent_chat(req: ChatRequest):
    logger.info(f"Chat agent demande : {req.message}")
    
    # Import dynamique de l'agent pour capter les fallbacks propres
    try:
        from agent import agent_executor, FallbackAgent
        
        # Tentative d'execution via l'agent ReAct de LangChain
        try:
            logger.info("Tentative d'appel du ReAct Agent de LangChain...")
            reponse = agent_executor.invoke({"input": req.message})
            return {"response": reponse["output"], "engine": "LangChain ReAct Agent"}
        except Exception as e:
            logger.warning(f"L'agent ReAct LangChain a rencontre une erreur ou le serveur LLM est hors-ligne : {e}")
            logger.info("Basculement sur le moteur d'analyse de secours FallbackAgent...")
            
            # Utilisation de notre FallbackAgent deterministe robuste
            reponse_fallback = FallbackAgent.solve(req.message)
            return {"response": reponse_fallback, "engine": "Fallback Static Agent"}
            
    except Exception as e:
        logger.error(f"Erreur d'importation ou d'execution de l'agent : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur critique de l'agent conversationnel : {str(e)}"
        )
