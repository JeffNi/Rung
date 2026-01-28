import random
import os
import re
from nltk.corpus import wordnet
import nltk
from utils import load_file

# Download required nltk data files if not already
nltk.download('wordnet')
nltk.download('omw-1.4')

# Natural contractions that should ALWAYS be used (not random)
NATURAL_CONTRACTIONS = {
    "I am": "I'm",
    "I have": "I've",
    "I would": "I'd",
    "that is": "that's",
    "it is": "it's",
    "cannot": "can't",
}

# Weak/hedging phrases to remove
WEAK_PHRASES = [
    r"\bI think,?\b",
    r"\bI believe,?\b", 
    r"\bkind of\b",
    r"\bsort of\b",
    r"\breally\b",
    r"\bvery\b",
    r"\bjust\b",
    r"\bactually\b",
    r"\bbasically\b",
    r"\bhonestly,?\b",
    r"\bto be frank,?\b",
    r"\bsimply put,?\b",
]

# Redundant phrases to clean up
REDUNDANT_PATTERNS = [
    (r"my whole thing is", "I focus on"),
    (r"is all about", "focuses on"),
    (r"that just clicks with me", "resonates with me"),
    (r"just feels like", "seems like"),
    (r"I'm keen to", "I want to"),
    (r"looking to", "want to"),
    (r"dive into", "work on"),
    (r"dive deeper", "explore"),
]

def apply_natural_contractions(text):
    """Apply contractions that sound natural (not random)"""
    for phrase, contraction in NATURAL_CONTRACTIONS.items():
        pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
        text = pattern.sub(contraction, text)
    return text

def remove_weak_language(text):
    """Remove hedging and filler words that weaken writing"""
    for pattern in WEAK_PHRASES:
        # Remove the phrase and clean up extra spaces/commas
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # Clean up double commas or comma-space issues
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r',\s+\.', '.', text)
    return text.strip()

def replace_redundant_phrases(text):
    """Replace overly casual or redundant phrases with cleaner alternatives"""
    for pattern, replacement in REDUNDANT_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def vary_sentence_starts(text):
    """Identify sentences starting with 'I' and mark them for variety"""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # Count consecutive 'I' starts
    i_streak = 0
    new_sents = []
    
    for sent in sentences:
        if sent.startswith('I ') or sent.startswith("I'm") or sent.startswith("I've"):
            i_streak += 1
            # If we have 3+ consecutive I sentences, that's a flag but we can't auto-fix
            # without understanding context, so we just track it
        else:
            i_streak = 0
        new_sents.append(sent)
    
    return ' '.join(new_sents)

def clean_formatting(text):
    """Fix formatting issues that make text look AI-generated"""
    # Replace em-dashes and double dashes with commas
    text = re.sub(r'—', ',', text)
    text = re.sub(r'--', ',', text)
    
    # Fix curly quotes to straight quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix comma spacing
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r'\s*\.\s*', '. ', text)
    
    return text.strip()

def clean_text(text):
    """
    Clean AI-generated text to sound more human without adding garbage.
    Focus: Remove weakness, not add random fillers.
    """
    # Apply natural contractions
    text = apply_natural_contractions(text)
    
    # Remove weak hedging language
    text = remove_weak_language(text)
    
    # Replace redundant casual phrases
    text = replace_redundant_phrases(text)
    
    # Vary sentence structure (tracking only for now)
    text = vary_sentence_starts(text)
    
    # Clean formatting
    text = clean_formatting(text)
    
    return text

if __name__ == "__main__":
    raw_text = load_file("outputs/cover_letter.txt")

    cleaned = clean_text(raw_text)
    output_path = os.path.join("outputs", f"cover_letter_cleaned.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)
    
