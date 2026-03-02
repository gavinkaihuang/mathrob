import os
import threading
import time
import logging

logger = logging.getLogger(__name__)

class GeminiTokenManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(GeminiTokenManager, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
                
            self._initialized = True
            self.keys = []
            
            # Load keys from environment
            keys_str = os.getenv("GEMINI_API_KEYS", "")
            if keys_str:
                # Comma separated
                self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            else:
                # Fallback to single old key if multiple not provided
                single_key = os.getenv("GEMINI_API_KEY", "")
                if single_key:
                    self.keys = [single_key.strip()]
                    
            if not self.keys:
                logger.warning("No Gemini API keys found in environment (GEMINI_API_KEYS or GEMINI_API_KEY)")
                
            # State tracking
            # Using a dict to map key -> status dict
            self.key_states = {k: {"status": "active", "cooldown_until": 0} for k in self.keys}
            self.current_index = 0
            self.cooldown_duration = 60 * 5 # 5 minutes cooldown for exhausted tokens
            
    def get_next_token(self) -> str:
        """
        Returns the next available token using round-robin.
        If all tokens are in cooldown, raises an exception or waits.
        """
        with self._lock:
            if not self.keys:
                raise ValueError("No API keys configured")
                
            now = time.time()
            start_index = self.current_index
            
            while True:
                candidate_key = self.keys[self.current_index]
                state = self.key_states[candidate_key]
                
                # Check if cooldown has expired
                if state["status"] == "cooldown" and now > state["cooldown_until"]:
                    state["status"] = "active"
                    logger.info(f"Token ending with ...{candidate_key[-4:]} exited cooldown.")
                    
                if state["status"] == "active":
                    # Advance for next time to achieve round-robin
                    self.current_index = (self.current_index + 1) % len(self.keys)
                    return candidate_key
                    
                # advance
                self.current_index = (self.current_index + 1) % len(self.keys)
                
                # Full loop check
                if self.current_index == start_index:
                    break
                    
            # If we get here, all keys are in cooldown
            logger.error("All Gemini API keys are currently exhausted or in cooldown.")
            raise Exception("All API keys are exhausted")
            
    def mark_token_exhausted(self, token: str):
        """
        Marks a token as exhausted (Rate Limit/Quota), placing it in cooldown.
        """
        with self._lock:
            if token in self.key_states:
                state = self.key_states[token]
                if state["status"] == "active":
                    state["status"] = "cooldown"
                    state["cooldown_until"] = time.time() + self.cooldown_duration
                    logger.warning(f"Token ending with ...{token[-4:]} marked as exhausted. Cooldown for {self.cooldown_duration}s.")
                    
    def get_status(self):
        """Returns the current status of all tokens (sanitized)"""
        with self._lock:
            status = []
            now = time.time()
            for k in self.keys:
                state = self.key_states[k]
                rem = max(0, state["cooldown_until"] - now) if state["status"] == "cooldown" else 0
                status.append({
                    "preview": f"...{k[-4:]}",
                    "status": "active" if state["status"] == "active" or rem == 0 else "cooldown",
                    "cooldown_remaining_sec": int(rem)
                })
            return status

# Create global instance
token_manager = GeminiTokenManager()
