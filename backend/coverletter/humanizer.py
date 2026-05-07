import random
import os
import re
from nltk.corpus import wordnet
import nltk
from utils import load_file

# Download required nltk data files if not already
nltk.download('wordnet')
nltk.download('omw-1.4')

# Contractions dictionary (expand or customize)
CONTRACTIONS = {
    "do not": "don't",
    "does not": "doesn't",
    "is not": "isn't",
    "are not": "aren't",
    "I am": "I'm",
    "I have": "I've",
    "cannot": "can't",
    "will not": "won't",
    "would not": "wouldn't",
    "should not": "shouldn't",
    "could not": "couldn't",
    "did not": "didn't",
}

FILLER_PHRASES = [
    "Honestly,",
    "To be frank,",
    "I've found that",
    "In my experience,",
    "Actually,",
    "Simply put,",
]

def get_synonym(word):
    """Get a synonym for a word using WordNet"""
    synonyms = wordnet.synsets(word)
    lemmas = set()
    for syn in synonyms:
        if syn is not None:
            for lemma in syn.lemmas():
                lem = lemma.name().replace('_', ' ')
                if lem.lower() != word.lower():
                    lemmas.add(lem)
    if lemmas:
        return random.choice(list(lemmas))
    else:
        return word

def apply_contractions(text):
    """Replace phrases with contractions randomly"""
    for phrase, contraction in CONTRACTIONS.items():
        # Replace with 50% probability
        def repl(match):
            return contraction if random.random() < 0.5 else match.group(0)
        pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
        text = pattern.sub(repl, text)
    return text

def insert_fillers(sentences):
    """Insert filler phrases at the start of some sentences"""
    new_sents = []
    for sent in sentences:
        if random.random() < 0.3:  # 30% chance to add filler
            filler = random.choice(FILLER_PHRASES)
            # Avoid double commas if sentence already starts with one
            if sent.startswith(filler):
                new_sents.append(sent)
            else:
                new_sents.append(filler + " " + sent[0].lower() + sent[1:])
        else:
            new_sents.append(sent)
    return new_sents

def synonym_swap(text, swap_prob=0.1):
    """Randomly swap some words with synonyms"""
    words = text.split()
    new_words = []
    for w in words:
        if random.random() < swap_prob and w.isalpha():
            new_words.append(get_synonym(w))
        else:
            new_words.append(w)
    return ' '.join(new_words)

def split_merge_sentences(sentences):
    """Randomly split or merge sentences"""
    i = 0
    new_sents = []
    while i < len(sentences):
        if i < len(sentences) -1 and random.random() < 0.2:
            # Merge current and next sentence
            merged = sentences[i].rstrip('.!?') + ', ' + sentences[i+1][0].lower() + sentences[i+1][1:]
            new_sents.append(merged)
            i += 2
        elif len(sentences[i]) > 100 and random.random() < 0.3:
            # Split long sentence roughly in the middle
            mid = len(sentences[i]) // 2
            # Find space near mid
            split_pos = sentences[i].find(' ', mid)
            if split_pos == -1:
                split_pos = mid
            new_sents.append(sentences[i][:split_pos] + '.')
            new_sents.append(sentences[i][split_pos+1:])
            i += 1
        else:
            new_sents.append(sentences[i])
            i += 1
    return new_sents

def clean_text(text):
    # Basic sentence splitter (can be replaced with nltk.sent_tokenize)
    sentences = re.split(r'(?<=[.!?]) +', text.strip())

    sentences = insert_fillers(sentences)
    sentences = split_merge_sentences(sentences)
    text = ' '.join(sentences)

    text = apply_contractions(text)
    text = synonym_swap(text)

    return text

if __name__ == "__main__":
    raw_text = load_file("outputs/cover_letter.txt")

    cleaned = clean_text(raw_text)
    output_path = os.path.join("outputs", f"cover_letter_cleaned.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)
    
