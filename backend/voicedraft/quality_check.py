"""
Quality checker for cover letters - detects common issues that make letters unprofessional
"""
import re
from collections import Counter

# Words that should not be repeated more than twice
AVOID_REPETITION = {'confident', 'excited', 'impressed', 'passionate', 'thrilled'}

# Sentence starts that should be varied
SENTENCE_START_PATTERNS = [
    r"^I'm\s+",
    r"^I\s+am\s+",
    r"^I\s+have\s+",
    r"^I\s+believe\s+",
    r"^I\s+think\s+",
    r"^I\s+feel\s+",
]

# Phrases that are unprofessional or generic
BANNED_PHRASES = [
    "to be honest",
    "honestly",
    "actually",
    "what drew me in",
    "I've always had a thing for",
    "social anxiety",
    "struggles",
    "weaknesses",
    "make a difference",
    "make a real impact",
    "I'm excited to apply",
    "I believe I'm a strong fit",
]

def check_sentence_start_repetition(text):
    """Check if the same sentence pattern is used too many times"""
    sentences = re.split(r'[.!?]\s+', text)
    
    start_counts = {}
    for pattern in SENTENCE_START_PATTERNS:
        count = sum(1 for sent in sentences if re.search(pattern, sent, re.IGNORECASE))
        if count > 3:  # More than 3 times is too much
            start_counts[pattern] = count
    
    return start_counts

def check_word_repetition(text):
    """Check for overused words"""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    word_counts = Counter(words)
    
    repeated = {}
    for word in AVOID_REPETITION:
        if word in word_counts and word_counts[word] > 2:
            repeated[word] = word_counts[word]
    
    return repeated

def check_banned_phrases(text):
    """Check for unprofessional or generic phrases"""
    found = []
    text_lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found

def validate_cover_letter(text):
    """
    Validate cover letter quality.
    Returns: (is_valid, issues_list)
    """
    issues = []
    
    # Check sentence start repetition
    start_reps = check_sentence_start_repetition(text)
    if start_reps:
        for pattern, count in start_reps.items():
            issues.append(f"Sentence pattern '{pattern}' used {count} times (limit: 3)")
    
    # Check word repetition
    word_reps = check_word_repetition(text)
    if word_reps:
        for word, count in word_reps.items():
            issues.append(f"Word '{word}' repeated {count} times (limit: 2)")
    
    # Check banned phrases
    banned = check_banned_phrases(text)
    if banned:
        for phrase in banned:
            issues.append(f"Unprofessional/generic phrase found: '{phrase}'")
    
    is_valid = len(issues) == 0
    return is_valid, issues

def print_quality_report(text):
    """Print a quality report for debugging"""
    is_valid, issues = validate_cover_letter(text)
    
    print("\n" + "="*60)
    print("QUALITY CHECK REPORT")
    print("="*60)
    
    if is_valid:
        print("[OK] PASSED - No major issues detected")
    else:
        print(f"[FAILED] {len(issues)} issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    print("="*60 + "\n")
    
    return is_valid, issues

