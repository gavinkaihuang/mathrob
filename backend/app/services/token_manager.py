import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import GeminiToken

logger = logging.getLogger(__name__)

class DBGeminiTokenManager:
    """
    Manages Gemini API tokens backed by a PostgreSQL database.
    Does not hold state in memory (except maybe local index for round-robin if desired,
    but we can also just fetch dynamically).
    To ensure true round-robin across requests, we can store a memory index, 
    but for absolute statelessness, we can just sort by last used or rely on random.
    Let's implement a simple in-memory current_index to round robin among available tokens.
    """
    
    def __init__(self):
        self.current_index = 0

    def get_available_token(self, db: Session) -> GeminiToken:
        """
        Fetches an available token from the database.
        A token is available if is_active=True and (cooldown_until is NULL or cooldown_until < now).
        """
        now = datetime.utcnow()
        
        available_tokens = db.query(GeminiToken).filter(
            GeminiToken.is_active == True,
            or_(
                GeminiToken.cooldown_until == None,
                GeminiToken.cooldown_until < now
            )
        ).order_by(GeminiToken.id).all()

        if not available_tokens:
            raise Exception("No active or available Gemini API keys found in the database. All keys might be exhausted.")

        # Round Robin selection
        self.current_index = (self.current_index + 1) % len(available_tokens)
        selected = available_tokens[self.current_index]
        
        # If it was in cooldown and we retrieved it, it means cooldown expired.
        # We can optionally clear the cooldown_until field here or leave it. 
        # Leaving it is fine as the query naturally filters it.
        if selected.cooldown_until and selected.cooldown_until < now:
            selected.cooldown_until = None
            db.commit()
            
        return selected

    def report_token_error(self, db: Session, token_id: int, token_name: str, error_msg: str):
        """
        When a token hits a Rate Limit (429) or Quota Exceeded error.
        Increments error_count and sets a 60-minute cooldown.
        """
        import datetime as dt
        token = db.query(GeminiToken).filter(GeminiToken.id == token_id).first()
        if token:
            token.error_count += 1
            # Set 60 min cooldown
            cooldown_time = datetime.utcnow() + dt.timedelta(minutes=60)
            token.cooldown_until = cooldown_time
            db.commit()
            
            logger.error(f"[TokenManager] Token '{token_name}' failed. Error: {error_msg}. Entering cooldown until {cooldown_time} UTC.")
        else:
            logger.error(f"[TokenManager] Attempted to report error for unknown Token ID {token_id}")

# Singleton instance
token_manager = DBGeminiTokenManager()
