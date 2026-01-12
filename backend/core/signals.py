import re
from sentence_transformers import util

# Keyword-based signals (Legacy/Explicit)
SIGNALS = {
    "stress": ["stress", "overwhelmed", "pressure", "burnout", "tension"],
    "fatigue": ["tired", "exhausted", "drained", "fatigue", "sleepy"],
    "low_mood": ["sad", "down", "depressed", "empty", "hopeless", "grief", "heartbreak", "crying"],
    "anxiety": ["anxious", "worried", "panic", "nervous", "scared", "fear"],
    "sleep_issues": ["sleep", "insomnia", "restless", "wake", "nightmare"],
    "self_worth": ["worthless", "guilt", "shame", "failure", "hate myself"],
    "attention": ["focus", "concentrate", "distracted", "scattered", "brain fog"],
    # Note: Violence and Vulnerability are handled specifically via PROTOTYPES or Regex, 
    # but keeping keys here for structure is fine.
    "violence_intent": [], 
    "vulnerability": ["confused", "don't know", "unsure", "maybe", "scared", "honest"],
}

# Embedding-based prototypes (Implicit/Semantic)
SIGNAL_PROTOTYPES = {
    "stress": "feeling overwhelmed, pressured, mentally overloaded",
    "low_mood": "sadness, emptiness, hopelessness, emotional heaviness",
    "anxiety": "worry, fear, panic, nervous anticipation",
    "fatigue": "exhaustion, low energy, burnout, tired all the time",
    "sleep_issues": "difficulty sleeping, insomnia, restless nights",
    "violence_intent": "intent to physically harm or kill another person, violent rage, making threats",
    "vulnerability": "admitting uncertainty or confusion while emotionally open, sharing something personal without strong distress",
}

RESPONSE_MODE_PROTOTYPES = {
    "answer": (
        "asking for a clear reason or explanation, frustrated by questions, "
        "wants a direct answer, says just answer or why does this happen"
    ),
    "explore": (
        "open to discussing feelings, reflecting, understanding more deeply, "
        "curious about patterns"
    ),
    "vent": (
        "expressing hurt, anger, frustration, wants to be heard, not asking for solutions"
    ),
}

# Advanced Logic Constants
VIOLENCE_PATTERNS = [
    r"\bi will (kill|hurt|attack|murder|smash)\b",
    r"\bi want to (kill|hurt|attack|murder|smash)\b",
    r"\bi am going to (kill|hurt|attack|murder|smash)\b",
    r"\bgonna (kill|hurt|attack|murder|smash)\b",
]

THRESHOLDS = {
    "violence_intent": 0.70,
    "low_mood": 0.50,
    "anxiety": 0.50,
    "vulnerability": 0.55,
}

NEGATIONS = ["not", "don't", "never", "wouldn't", "won't", "cant", "can't"]

PROTOTYPE_EMBEDDINGS = {}
RESPONSE_MODE_EMBEDDINGS = {}

def decay_signals(memory, decay=0.85):
    """Reduces signal intensity to represent emotional momentum."""
    # Ensure memory['signals'] exists and has all keys
    if "signals" not in memory:
        memory["signals"] = {k: 0.0 for k in SIGNALS.keys()}
        
    for k in memory["signals"]:
        memory["signals"][k] *= decay

def is_negated(text, keyword, window=3):
    """Checks if a keyword is preceded by a negation in a small window."""
    tokens = text.lower().split()
    # Simple token check - strict matching
    # Find all indices of keyword (substring match in token)
    matches = [i for i, t in enumerate(tokens) if keyword in t]
    
    for i in matches:
        start = max(0, i - window)
        # check negation in the window before the keyword
        if any(n in tokens[start:i] for n in NEGATIONS):
            return True
    return False

def extract_signals(text, memory, model=None):
    text_lower = text.lower()
    
    # Ensure memory structure
    if "signals" not in memory:
        memory["signals"] = {k: 0.0 for k in SIGNALS.keys()}
    
    # 0. Apply Decay
    decay_signals(memory)
    
    # 1. Hard Violence Override (Regex)
    # Check regex patterns first for maximum safety
    for pattern in VIOLENCE_PATTERNS:
        if re.search(pattern, text_lower):
            memory["signals"]["violence_intent"] = 1.0
            memory["stage"] = "safety"
            memory["lock_stage"] = True
            return # Exit immediately to preventing softening
            
    # 2. Keyword Extraction (Explicit) with Negation
    for signal, keywords in SIGNALS.items():
        if signal == "violence_intent": continue # Skip keyword list for violence, rely on regex/embedding
        
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text_lower):
                if not is_negated(text_lower, kw):
                    # Ensure the signal key exists
                    if signal not in memory["signals"]: memory["signals"][signal] = 0.0
                    memory["signals"][signal] += 1
                
    # 3. Embedding Extraction (Implicit)
    if model and SIGNAL_PROTOTYPES:
        # Lazy load prototype embeddings
        if not PROTOTYPE_EMBEDDINGS:
            for sig, desc in SIGNAL_PROTOTYPES.items():
                PROTOTYPE_EMBEDDINGS[sig] = model.encode(desc, convert_to_tensor=True, show_progress_bar=False)
        
        # Encode user text
        try:
            # OPTIMIZATION: Use pre-computed embedding if available (not passed yet, but good for future)
            # For now, just disable progress bar
            user_emb = model.encode(text, convert_to_tensor=True, show_progress_bar=False)
            
            # Compare
            for sig, proto_emb in PROTOTYPE_EMBEDDINGS.items():
                threshold = THRESHOLDS.get(sig, 0.45) # Default 0.45
                score = util.cos_sim(user_emb, proto_emb).item()
                
                if score > threshold:
                    # Special Safety Check for Violence Embedding
                    if sig == "violence_intent":
                         # Extra high threshold was processed.
                         memory["signals"]["violence_intent"] = 1.0
                         memory["stage"] = "safety"
                         memory["lock_stage"] = True
                         return
                    
                    # Vulnerability Check - Don't trigger if high distress
                    if sig == "vulnerability":
                         if memory["signals"].get("violence_intent", 0) > 0:
                             continue
                    
                    if sig not in memory["signals"]: memory["signals"][sig] = 0.0
                    memory["signals"][sig] += 0.5
        except Exception as e:
            print(f"Embedding extraction failed: {e}")

def detect_response_mode(text, model, min_confidence=0.55):
    if not model:
        return "explore"
        
    try:
        if not RESPONSE_MODE_EMBEDDINGS:
                for mode, desc in RESPONSE_MODE_PROTOTYPES.items():
                    RESPONSE_MODE_EMBEDDINGS[mode] = model.encode(desc, convert_to_tensor=True, show_progress_bar=False)
        
        user_emb = model.encode(text, convert_to_tensor=True, show_progress_bar=False)
        scores = {}
        for mode, proto_emb in RESPONSE_MODE_EMBEDDINGS.items():
            scores[mode] = util.cos_sim(user_emb, proto_emb).item()
        
        best_mode = max(scores, key=scores.get)
        if scores[best_mode] < min_confidence:
            return "explore"
            
        return best_mode
    except Exception:
        return "explore"
