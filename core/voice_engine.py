#!/usr/bin/env python3
"""
Voice Notes & Audio Pitch Studio Engine (ElevenLabs & Composio)
================================================================================
Générateur de scripts et d'enregistrements vocaux personnalisés pour WhatsApp :
- Les notes vocales WhatsApp convertissent jusqu'à 3x plus que les messages écrits
- Personnalisation vocale authentique incarnant Dave Sagbo (vouvoiement, ton chaleureux)
- Synthèse audio MP3 haute fidélité via ElevenLabs sur l'infrastructure instantanée Composio
- Mise en cache locale dans web/static/audio/voice_notes/ pour lecture web et partage direct
- Sauvegarde systématique dans l'historique des interactions crm_lead_messages

Auteur : Dave Sagbo - Système Commercial IA
"""

import os
import re
import json
import time
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional
from modules.composio_client import call_composio_tool
from core.database_store import get_connection

logger = logging.getLogger("VoiceEngine")

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_STORAGE_DIR = BASE_DIR / "web" / "static" / "audio" / "voice_notes"
AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Voix masculine francophone / internationale d'excellence pour Dave Sagbo :
# "pNInz6obpgDQGcFmaJgB" (Adam) : Voix posée, profonde, chaleureuse et très humaine (adieu le ton robotique IA)
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

VOICE_PROFILES = {
    "adam_pose": {
        "id": "pNInz6obpgDQGcFmaJgB",
        "name": "Dave Sagbo (Posé & Calme)",
        "description": "Voix grave, posée, naturelle et rassurante. Idéale pour WhatsApp B2B.",
        "settings": {"stability": 0.75, "similarity_boost": 0.85, "style": 0.0, "use_speaker_boost": True}
    },
    "george_chaleureux": {
        "id": "JBFqnCBsd6RMkjVDRZzb",
        "name": "Dave Sagbo (Chaleureux & Posé)",
        "description": "Voix feutrée et chaleureuse avec un ton très humain et bienveillant.",
        "settings": {"stability": 0.72, "similarity_boost": 0.85, "style": 0.0, "use_speaker_boost": True}
    },
    "roger_dynamique": {
        "id": "CwhRBWXzGAHq8TQ4Fs17",
        "name": "Dave Sagbo (Assuré & Direct)",
        "description": "Voix assurée avec une pointe de dynamisme entrepreneurial.",
        "settings": {"stability": 0.70, "similarity_boost": 0.80, "style": 0.0, "use_speaker_boost": True}
    }
}


class VoiceEngine:
    def __init__(self):
        self.voice_id = DEFAULT_VOICE_ID
        self.voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.0,
            "use_speaker_boost": True
        }

    def generate_voice_script(
        self,
        lead_data: Optional[Dict[str, Any]] = None,
        context_type: str = "accroche_decouverte",
        custom_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Génère un script vocal court, naturel, posé et humain incarnant Dave Sagbo.
        Inclut des micro-pauses (...) pour une diction calme, fluide et authentique.
        """
        data = lead_data or {}
        nom = data.get("nom_complet") or data.get("nom_lead") or "Cher Partenaire"
        prenom = data.get("prenom") or nom.split()[0]
        poste = data.get("poste") or "Responsable"
        interet = data.get("centre_interet") or data.get("notes") or "votre développement commercial"
        entreprise = data.get("entreprise") or data.get("nom_entreprise") or ""

        script_text = ""
        speech_notes = ""

        if context_type == "accroche_decouverte":
            ent_mention = f" chez {entreprise}" if entreprise else ""
            script_text = (
                f"Bonjour {prenom}... C'est Dave Sagbo. "
                f"Je vous laisse ce court vocal pour faire votre connaissance{ent_mention}. "
                f"J'ai vu votre intérêt concernant {interet}... "
                f"Dites-moi, quelle est votre priorité commerciale du moment ?"
            )
            speech_notes = "Voix posée, humaine, calme et bienveillante."

        elif context_type == "relance_valeur":
            script_text = (
                f"Bonjour {prenom}... C'est Dave. "
                f"Petit vocal rapide pour prendre de vos nouvelles. "
                f"Dans la plupart des entreprises qu'on accompagne sur {interet}... "
                f"le plus gros défi reste souvent la conversion des contacts en clients payants. "
                f"Est-ce que c'est un point sur lequel vous avancez cette semaine ?"
            )
            speech_notes = "Ton calme d'entrepreneur à entrepreneur, axé valeur et écoute."

        elif context_type == "cloture_demo":
            script_text = (
                f"Bonjour {prenom}... C'est Dave Sagbo. "
                f"Au vu de nos échanges, je suis convaincu qu'on peut vous faire gagner un temps précieux et sécuriser vos ventes. "
                f"Seriez-vous partant pour 15 minutes d'échange sans engagement... demain ou après-demain ?"
            )
            speech_notes = "Ton posé, serein, professionnel et cordial."

        else:
            # Script sur-mesure ou général
            script_text = (
                f"Bonjour {prenom}... C'est Dave Sagbo. "
                f"Ravi d'échanger avec vous. "
                f"Je reste disponible pour échanger sur vos objectifs et voir comment propulser vos résultats."
            )
            speech_notes = "Ton naturel, calme et humain."

        # Nettoyage pour la synthèse TTS (retirer éventuels emojis et balises)
        clean_text = re.sub(r'[^\w\s\.,\?!éèêëàâäôöûüùçîïÉÈÊÀÂÔÛÎÇ\'-]', '', script_text).strip()
        word_count = len(clean_text.split())
        estimated_duration = max(5, round(word_count / 2.3))

        return {
            "lead_name": prenom,
            "context": context_type,
            "script_text": script_text,
            "clean_text": clean_text,
            "speech_notes": speech_notes,
            "estimated_duration_seconds": estimated_duration
        }

    def synthesize_voice_note(
        self,
        text: str,
        lead_id: Optional[int] = None,
        voice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envoie le texte à ElevenLabs via Composio, télécharge le fichier MP3
        dans web/static/audio/voice_notes/ et renvoie l'URL locale et S3.
        """
        target_voice = voice_id or self.voice_id
        clean_text = re.sub(r'[^\w\s\.,\?!éèêëàâäôöûüùçîïÉÈÊÀÂÔÛÎÇ\'-]', '', text).strip()

        if not clean_text:
            return {"success": False, "error": "Texte vocal vide"}

        try:
            logger.info(f"Synthèse vocale ElevenLabs via Composio (Voice ID: {target_voice}, {len(clean_text)} car)...")
            res = call_composio_tool("ELEVENLABS_TEXT_TO_SPEECH", {
                "voice_id": target_voice,
                "text": clean_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": getattr(self, "voice_settings", {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.0,
                    "use_speaker_boost": True
                })
            }, timeout=40)

            if not res or not isinstance(res, dict):
                return {"success": False, "error": "Aucune réponse de synthèse ElevenLabs"}

            # Extraction de l'URL S3 ou fichier retourné
            s3url = None
            if "file" in res and isinstance(res["file"], dict):
                s3url = res["file"].get("s3url") or res["file"].get("url")
            elif "s3url" in res:
                s3url = res.get("s3url")
            elif "audio_url" in res:
                s3url = res.get("audio_url")

            if not s3url:
                logger.warning(f"Retour inattendu Composio TTS : {res}")
                return {"success": False, "error": "Fichier audio non trouvé dans la réponse", "raw": res}

            # Nom de fichier unique pour le stockage local
            ts = int(time.time())
            lead_tag = f"lead_{lead_id}_" if lead_id else "sim_"
            filename = f"vocal_{lead_tag}{ts}.mp3"
            local_path = AUDIO_STORAGE_DIR / filename

            # Téléchargement du MP3 généré
            req = urllib.request.Request(s3url, headers={"User-Agent": "Sales-Voice-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                with open(local_path, "wb") as f:
                    f.write(resp.read())

            local_url = f"/static/audio/voice_notes/{filename}"
            logger.info(f"Note vocale MP3 générée et sauvegardée : {local_url} ({os.path.getsize(local_path)} octets)")

            return {
                "success": True,
                "filename": filename,
                "audio_url": local_url,
                "s3url": s3url,
                "text": clean_text,
                "voice_id": target_voice
            }
        except Exception as e:
            logger.error(f"Erreur synthèse ElevenLabs ({target_voice}) : {e}")
            return {"success": False, "error": str(e)}

    def generate_and_save_voice_note(
        self,
        lead_id: int,
        context_type: str = "accroche_decouverte",
        custom_text: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Point d'entrée complet pour générer, synthétiser et enregistrer
        une note vocale pour un prospect dans crm_lead_messages.
        RÈGLE : Soit le message écrit, soit la note vocale, mais pas les deux ensemble.
        """
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
        row = c.fetchone()
        conn.close()

        lead = dict(row) if row else {}
        if not lead:
            return {"success": False, "error": f"Prospect #{lead_id} non trouvé"}

        # Génération ou utilisation du texte personnalisé
        if custom_text and len(custom_text.strip()) > 5:
            script_data = {
                "script_text": custom_text.strip(),
                "clean_text": custom_text.strip(),
                "context": context_type
            }
        else:
            script_data = self.generate_voice_script(lead, context_type=context_type)

        synth_res = self.synthesize_voice_note(script_data["clean_text"], lead_id=lead_id)
        if not synth_res.get("success"):
            return synth_res

        audio_url = synth_res["audio_url"]
        # Sauvegarde exclusive de l'audio avec métadonnée technique de transcription
        message_formatted = f"[AUDIO: {audio_url}]\n[TRANSCRIPT: {script_data['script_text']}]"

        # Sauvegarde dans SQLite crm_lead_messages
        try:
            canal = channel or lead.get("canal_actuel") or lead.get("source_canal") or "WHATSAPP"
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO crm_lead_messages (lead_id, channel, sender, message, status, timestamp)
                VALUES (?, ?, 'Dave Sagbo (Vocal WhatsApp)', ?, 'DELIVERED', datetime('now'))
            """, (lead_id, canal, message_formatted))
            c.execute("""
                UPDATE crm_leads
                SET last_interaction = datetime('now'),
                    updated_at = datetime('now')
                WHERE id = ?
            """, (lead_id,))
            conn.commit()
            conn.close()
        except Exception as e_db:
            logger.warning(f"Erreur enregistrement message vocal dans crm_lead_messages : {e_db}")

        return {
            "success": True,
            "lead_id": lead_id,
            "audio_url": audio_url,
            "s3url": synth_res.get("s3url"),
            "script_text": script_data["script_text"],
            "message_formatted": message_formatted,
            "context": context_type
        }


# Instance globale réutilisable
voice_engine = VoiceEngine()
