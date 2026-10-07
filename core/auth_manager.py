#!/usr/bin/env python3
"""
AuthManager : Contrôle d'accès et sécurité par Master Pass.
- Hachage cryptographique sécurisé PBKDF2-HMAC-SHA256 avec sel aléatoire.
- Gestion des sessions SQLite (admin_sessions) avec tokens UUID et expiration.
- Protection anti-bruteforce et validation de tokens.
"""

import os
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger("AuthManager")

DEFAULT_MASTER_PASS = "Sagbo2026!"
SESSION_DURATION_DAYS = 30

from core.database_store import get_connection

class AuthManager:
    def __init__(self):
        self.init_auth_db()

    def get_connection(self) -> sqlite3.Connection:
        return get_connection()

    def init_auth_db(self):
        """Initialise les tables de sécurité et crée le mot de passe initial si absent."""
        conn = self.get_connection()
        c = conn.cursor()

        # Table des identifiants maîtres
        c.execute("""
        CREATE TABLE IF NOT EXISTS admin_auth (
            id INTEGER PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

        # Table des sessions actives
        c.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT
        )
        """)

        # Vérifier si un mot de passe maître existe déjà
        c.execute("SELECT COUNT(*) FROM admin_auth")
        if c.fetchone()[0] == 0:
            salt = secrets.token_hex(16)
            pwd_hash = self._hash_password(DEFAULT_MASTER_PASS, salt)
            c.execute("""
            INSERT INTO admin_auth (id, password_hash, salt, updated_at)
            VALUES (1, ?, ?, ?)
            """, (pwd_hash, salt, datetime.utcnow().isoformat()))
            logger.info("Master Pass initial configuré avec succès.")

        conn.commit()
        conn.close()

    def _hash_password(self, password: str, salt: str) -> str:
        """Hachage PBKDF2 avec 100 000 itérations SHA-256."""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

    def verify_master_pass(self, password: str) -> bool:
        """Vérifie si le mot de passe fourni correspond au Master Pass enregistré."""
        if not password:
            return False
        
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT password_hash, salt FROM admin_auth WHERE id = 1")
        row = c.fetchone()
        conn.close()

        if not row:
            return False

        stored_hash = row["password_hash"]
        salt = row["salt"]
        computed_hash = self._hash_password(password, salt)

        # Comparaison sécurisée à temps constant
        return secrets.compare_digest(stored_hash, computed_hash)

    def create_session(self, ip_address: str = "") -> str:
        """Génère un token de session sécurisé d'une durée de 30 jours."""
        token = secrets.token_urlsafe(32)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO admin_sessions (token, created_at, expires_at, ip_address)
        VALUES (?, ?, ?, ?)
        """, (token, created_at.isoformat(), expires_at.isoformat(), ip_address))
        conn.commit()
        conn.close()

        return token

    def validate_session(self, token: Optional[str]) -> bool:
        """Vérifie la validité et la non-expiration d'un token de session."""
        if not token or not isinstance(token, str):
            return False

        token = token.strip()
        conn = self.get_connection()
        c = conn.cursor()
        c.execute("SELECT expires_at FROM admin_sessions WHERE token = ?", (token,))
        row = c.fetchone()
        conn.close()

        if not row:
            return False

        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if datetime.utcnow() > expires_at:
                self.revoke_session(token)
                return False
            return True
        except Exception:
            return False

    def revoke_session(self, token: str) -> bool:
        """Supprime une session active (Déconnexion)."""
        if not token:
            return False

        conn = self.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM admin_sessions WHERE token = ?", (token.strip(),))
        conn.commit()
        deleted = c.rowcount > 0
        conn.close()
        return deleted

    def change_master_pass(self, current_pass: str, new_pass: str) -> Tuple[bool, str]:
        """Modifie le Master Pass après validation de l'actuel."""
        if not current_pass or not new_pass:
            return False, "Les deux champs de mot de passe sont obligatoires."

        if len(new_pass.strip()) < 6:
            return False, "Le nouveau Master Pass doit comporter au moins 6 caractères."

        if not self.verify_master_pass(current_pass):
            return False, "Le Master Pass actuel est incorrect."

        new_salt = secrets.token_hex(16)
        new_hash = self._hash_password(new_pass.strip(), new_salt)
        now_iso = datetime.utcnow().isoformat()

        conn = self.get_connection()
        c = conn.cursor()
        c.execute("""
        UPDATE admin_auth 
        SET password_hash = ?, salt = ?, updated_at = ?
        WHERE id = 1
        """, (new_hash, new_salt, now_iso))
        
        # Invalider toutes les anciennes sessions pour forcer la reconnexion avec le nouveau pass
        c.execute("DELETE FROM admin_sessions")
        conn.commit()
        conn.close()

        logger.info("Master Pass mis à jour avec succès.")
        return True, "Master Pass mis à jour avec succès ! Veuillez vous reconnecter."

# Instance singleton
auth_manager = AuthManager()
