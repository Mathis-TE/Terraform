import sys
import re
from pathlib import Path

# S'assurer que le dossier backend est dans le path de recherche
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from tools import outil_estimation_ml

# --- Imports Resilients pour LangChain ---
HAS_LANGCHAIN = False
try:
    from langchain_community.llms import Ollama
    from langchain.tools import tool
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain_core.prompts import PromptTemplate
    HAS_LANGCHAIN = True
except ImportError:
    # Definition d'un mock minimaliste pour eviter les crashs de syntaxe
    def tool(func):
        return func
    print("[WARNING] LangChain ou LangChain-Community n'est pas installe. Le mode ReAct Agent ne sera pas disponible.")

# --- Definition de l'Outil pour LangChain ---

@tool
def calculateur_immobilier(input_string: str) -> str:
    """
    Utilise cet outil UNIQUEMENT pour estimer le prix d'un bien immobilier en Ile-de-France.
    L'entree de l'outil doit etre formatee exactement comme ceci : surface,pieces,code_postal,type_bien
    Exemple d'entree : 65,3,92100,Appartement
    """
    try:
        parametres = input_string.split(',')
        surface = int(parametres[0].strip())
        pieces = int(parametres[1].strip())
        code_postal = parametres[2].strip()
        type_bien = parametres[3].strip()
        
        # Appeler le moteur ML (return_dict=False renvoie la version rédigée détaillée)
        return outil_estimation_ml(
            surface=surface, 
            pieces=pieces, 
            code_postal=code_postal, 
            type_bien=type_bien,
            return_dict=False
        )
    except Exception as e:
        return ("Erreur de format. Demande poliment a l'utilisateur de preciser les 4 parametres requis "
                "dans l'ordre : la surface (m2), le nombre de pieces, le code postal de 5 chiffres "
                "en Ile-de-France, et le type de bien (Maison ou Appartement).")

outils = [calculateur_immobilier]

# --- Configuration et Initialisation du LLM local ---

llm = None
template = ""
prompt = None
agent_logic = None
agent_executor = None

if HAS_LANGCHAIN:
    # Par défaut, on cherche Ollama en local. Si le port change ou si LM Studio est utilisé, 
    # on peut adapter la base_url via l'environnement.
    try:
        llm = Ollama(model="llama3", temperature=0.2, timeout=10)
    except Exception as e:
        print(f"[WARNING] Impossible d'initialiser Ollama : {e}")

    # Prompt Template ReAct classique en français
    template = """Tu es Geo-Estate AI, un expert de l'estimation immobiliere en Ile-de-France, professionnel, courtois et precis.
Ton role est de conseiller et guider les utilisateurs sur la valeur de leurs biens immobiliers en s'appuyant sur des donnees et des modeles statistiques.

REGLES STRICTES :
1. Tu NE DOIS JAMAIS inventer un prix. 
2. Si on te demande d'estimer un bien, tu DOIS obligatoirement utiliser l'outil 'calculateur_immobilier'.
3. Si l'utilisateur ne fournit pas toutes les informations (surface, nombre de pieces, code postal francilien, type de bien Appartement/Maison), demande-les lui poliment une par une avant d'appeler l'outil.
4. Une fois que tu as obtenu la reponse de l'outil, integre les details micro-locaux (GPS, DPE, Georisques, insecurite) dans ta reponse finale pour valoriser l'analyse.

Tu as acces aux outils suivants :
{tools}

Pour utiliser un outil, utilise le format suivant :
Question: la question de l'utilisateur
Thought: tu dois toujours reflechir a ce que tu dois faire
Action: l'action a entreprendre, doit etre l'un des [{tool_names}]
Action Input: l'entree pour l'action (format: surface,pieces,code_postal,type_bien)
Observation: le resultat de l'action
... (ce cycle Thought/Action/Action Input/Observation peut se repeter N fois)
Thought: je connais maintenant la reponse finale
Final Answer: la reponse finale de Geo-Estate AI a l'utilisateur. Sois professionnel, redige en francais structure avec des puces.

Question: {input}
Thought:{agent_scratchpad}"""

    try:
        prompt = PromptTemplate.from_template(template)
        if llm:
            agent_logic = create_react_agent(llm, outils, prompt)
            agent_executor = AgentExecutor(
                agent=agent_logic,
                tools=outils,
                verbose=True,
                handle_parsing_errors=True
            )
    except Exception as e:
        print(f"[WARNING] Erreur d'initialisation de la chaine d'agent : {e}")

# --- Agent de Secours Déterministe et Robuste (FallbackAgent) ---

class FallbackAgent:
    """
    Moteur d'analyse statique de secours si le LLM local est injoignable.
    Analyse le message de l'utilisateur, extrait les critères immobiliers, 
    et produit une réponse structurée et personnalisée de qualité professionnelle.
    """
    
    @staticmethod
    def solve(message: str) -> str:
        msg = message.lower()
        
        # Extraction de la surface (m2 ou m²)
        surface_match = re.search(r'(\d+)\s*(?:m2|m²|metre|mètre)', msg)
        # Extraction du nombre de pièces (pieces ou pièces)
        pieces_match = re.search(r'(\d+)\s*(?:piece|pièce|p\b)', msg)
        # Extraction du code postal (5 chiffres)
        cp_match = re.search(r'\b(75\d{3}|77\d{3}|78\d{3}|91\d{3}|92\d{3}|93\d{3}|94\d{3}|95\d{3})\b', msg)
        # Extraction du type de bien
        type_bien = "Appartement"  # Par défaut
        if "maison" in msg or "pavillon" in msg or "villa" in msg:
            type_bien = "Maison"
        elif "appartement" in msg or "studio" in msg or "appt" in msg:
            type_bien = "Appartement"

        # Si on arrive à identifier les paramètres clés
        if surface_match and pieces_match and cp_match:
            try:
                surface = int(surface_match.group(1))
                pieces = int(pieces_match.group(1))
                code_postal = cp_match.group(1)
                
                # S'assurer que les valeurs sont dans des bornes valides pour le modèle
                surface = max(10, min(300, surface))
                pieces = max(1, min(10, pieces))
                
                # Lancement de l'estimation ML
                res_ml = outil_estimation_ml(
                    surface=surface,
                    pieces=pieces,
                    code_postal=code_postal,
                    type_bien=type_bien,
                    return_dict=True
                )
                
                if "erreur" in res_ml:
                    return f"Désolé, une erreur technique est survenue lors de l'estimation : {res_ml['erreur']}"
                
                # Formatage de la réponse
                prix = res_ml['prix_estime']
                return (
                    f"Bonjour ! En tant que **Geo-Estate AI** (Moteur de secours), j'ai analysé votre demande.\n\n"
                    f"Grâce à notre modèle d'apprentissage statistique entraîné sur l'Île-de-France, "
                    f"voici l'analyse d'estimation pour votre bien :\n\n"
                    f"### 📊 Rapport d'Estimation Immobilière\n"
                    f"* **Type de bien** : {type_bien}\n"
                    f"* **Caractéristiques** : {surface} m² — {pieces} pièces\n"
                    f"* **Localisation** : Secteur {code_postal} (Département {res_ml['departement']})\n"
                    f"* **Valeur estimée** : **{prix:,.0f} €**\n\n"
                    f"### 📍 Indicateurs Micro-locaux du Secteur\n"
                    f"* **Performance énergétique** : Classe **{res_ml['classe_dpe']}** (DPE médian de la zone)\n"
                    f"* **Risques environnementaux** : **{res_ml['score_georisques']:.1f}/10** (Géorisques)\n"
                    f"* **Indice de sécurité** : **{res_ml['score_delinquance']:.1f}/10** (Taux de délinquance départemental)\n"
                    f"* **Coordonnées de calcul** : {res_ml['latitude']:.4f}, {res_ml['longitude']:.4f}\n\n"
                    f"Cette estimation brute est basée sur 787 260 transactions de 2021 à 2025. "
                    f"N'hésitez pas à me donner d'autres critères pour affiner cette analyse!"
                )
            except Exception as e:
                pass
                
        # Message d'accueil et d'explication si les paramètres sont incomplets
        return (
            "Bonjour ! Je suis **Geo-Estate AI**, votre expert d'estimation immobilière en Île-de-France.\n\n"
            "Je peux estimer instantanément n'importe quel bien de la région grâce à nos algorithmes de "
            "Machine Learning et nos indicateurs de risques enrichis.\n\n"
            "Pour produire votre rapport d'estimation, veuillez m'indiquer :\n"
            "1. La **surface habitable** en m²\n"
            "2. Le **nombre de pièces** principales\n"
            "3. Le **code postal** à 5 chiffres en Île-de-France (ex: 92100, 75015)\n"
            "4. Le **type de bien** (*Maison* ou *Appartement*)\n\n"
            "Exemple : *\"Estime un appartement de 65m2 avec 3 pièces à Boulogne 92100\"*"
        )

# Test rapide en ligne de commande
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print("--- Test du FallbackAgent de secours ---")
    question = "Je veux estimer une maison de 120m2 avec 5 pieces au code postal 78000"
    print(f"Question : {question}\n")
    print(FallbackAgent.solve(question))
