"""
core/session_manager.py
=======================
Thread-safe Multi-Turn Working Memory & Conversational State Manager.
Maintains session context across user turns so follow-up inquiries
("What is its debt?", "Im asking for Adani Enterprise") seamlessly
inherit or slot-fill the target entity without needing an explicit dropdown.
"""

import time
import threading
from typing import Dict, Any, Optional, List

# Session TTL: 30 minutes of inactivity
SESSION_TTL_SECONDS = 1800

class ConversationSession:
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.last_accessed: float = time.time()
        self.active_symbol: Optional[str] = None
        self.active_company_name: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.last_prompt_type: Optional[str] = None  # e.g. 'CLARIFY_SYMBOL', 'DISAMBIGUATE'
        self.last_compared_symbols: List[str] = []
        self.user_name: Optional[str] = None
        self.history: List[Dict[str, str]] = []

    def touch(self):
        self.last_accessed = time.time()

    def set_symbol(self, symbol: Optional[str], company_name: Optional[str] = None):
        self.touch()
        if symbol:
            self.active_symbol = symbol.upper().strip()
            if company_name:
                self.active_company_name = company_name

    def clear_symbol(self):
        self.touch()
        self.active_symbol = None
        self.active_company_name = None

    def set_compared_symbols(self, sym1: str, sym2: str):
        self.touch()
        self.last_compared_symbols = [sym1.upper().strip(), sym2.upper().strip()]

    def set_user_name(self, name: str):
        self.touch()
        if name and name.strip():
            self.user_name = name.strip()

    def add_turn(self, role: str, content: str):
        self.touch()
        self.history.append({"role": role, "content": content, "timestamp": str(time.time())})
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_symbol": self.active_symbol,
            "active_company_name": self.active_company_name,
            "last_intent": self.last_intent,
            "last_prompt_type": self.last_prompt_type,
            "last_compared_symbols": self.last_compared_symbols,
            "user_name": self.user_name,
            "turns_count": len(self.history)
        }


class SessionManager:
    """In-memory thread-safe session registry with automatic cleanup."""

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    def get_session(self, session_id: Optional[str]) -> ConversationSession:
        if not session_id or not session_id.strip():
            session_id = "default_terminal_session"
            
        with self._lock:
            now = time.time()
            # Periodic cleanup of expired sessions
            expired = [sid for sid, s in self._sessions.items() if (now - s.last_accessed) > SESSION_TTL_SECONDS]
            for sid in expired:
                del self._sessions[sid]

            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationSession(session_id)
            else:
                self._sessions[session_id].touch()

            return self._sessions[session_id]

    def clear_session(self, session_id: Optional[str]):
        if not session_id:
            return
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]


# Global singleton
_GLOBAL_SESSION_MANAGER = SessionManager()

def get_session_manager() -> SessionManager:
    return _GLOBAL_SESSION_MANAGER

def get_session(session_id: Optional[str] = None) -> ConversationSession:
    return _GLOBAL_SESSION_MANAGER.get_session(session_id)
