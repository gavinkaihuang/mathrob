from datetime import datetime, timedelta
from typing import Tuple

def calculate_next_review(
    ease_factor: float, 
    interval: int, 
    repetitions: int, 
    score: int
) -> Tuple[float, int, int, datetime]:
    """
    SM-2 Algorithm Implementation for MathRob.
    
    Scores:
    0: Not Understood (完全不会)
    1: Half Understood (半知半解)
    2: Mastered (完全掌握)
    
    Returns: (new_ease_factor, new_interval, new_repetitions, next_review_date)
    """
    
    if score == 0:
        # Reset interval, SIGNIFICANTLY decrease ease factor
        new_interval = 1
        new_repetitions = 0
        new_ease_factor = max(1.3, ease_factor - 0.5)
    elif score == 1:
        # Maintain or slight increase in interval, slight decrease in ease factor
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 3
        else:
            new_interval = max(1, int(interval * 1.2))
        
        new_repetitions = repetitions + 1
        new_ease_factor = max(1.3, ease_factor - 0.2)
    else: # score == 2 (Mastered)
        # Standard SM-2 logic with some tuning
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = max(1, int(interval * ease_factor))
        
        new_repetitions = repetitions + 1
        # Increase ease factor slightly
        new_ease_factor = ease_factor + 0.1
        
    next_review_date = datetime.utcnow() + timedelta(days=new_interval)
    
    return new_ease_factor, new_interval, new_repetitions, next_review_date
