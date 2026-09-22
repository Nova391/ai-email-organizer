import math
import re
import json
from collections import defaultdict
from pathlib import Path

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for", 
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", 
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", 
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", 
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", 
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", 
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", 
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", 
    "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself", "yourselves"
}

def tokenize(text):
    if not text:
        return []
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS and not t.isnumeric()]

class NaiveBayesClassifier:
    def __init__(self):
        self.class_counts = defaultdict(int)
        self.word_counts = defaultdict(lambda: defaultdict(int))
        self.total_words_per_class = defaultdict(int)
        self.vocab = set()
        self.total_docs = 0

    def fit(self, texts, labels):
        self.total_docs = len(texts)
        for text, label in zip(texts, labels):
            self.class_counts[label] += 1
            tokens = tokenize(text)
            for token in tokens:
                self.word_counts[label][token] += 1
                self.total_words_per_class[label] += 1
                self.vocab.add(token)

    def predict_one(self, text):
        tokens = tokenize(text)
        vocab_size = len(self.vocab)
        best_class = None
        best_log_prob = -float("inf")
        class_scores = {}

        for c, count in self.class_counts.items():
            log_prior = math.log(count / self.total_docs)
            total_words_c = self.total_words_per_class[c]
            log_likelihood = 0.0
            
            for token in tokens:
                if token in self.vocab:
                    word_freq = self.word_counts[c][token]
                    log_likelihood += math.log((word_freq + 1) / (total_words_c + vocab_size))
            
            score = log_prior + log_likelihood
            class_scores[c] = score
            if score > best_log_prob:
                best_log_prob = score
                best_class = c

        max_score = max(class_scores.values())
        exp_scores = {c: math.exp(s - max_score) for c, s in class_scores.items()}
        sum_exp = sum(exp_scores.values())
        probs = {c: round(s / sum_exp, 4) for c, s in exp_scores.items()}

        confidence = probs.get(best_class, 0.0)
        return best_class, confidence, probs

    def predict(self, texts):
        return [self.predict_one(t)[0] for t in texts]

    def save(self, filepath):
        data = {
            "class_counts": dict(self.class_counts),
            "word_counts": {k: dict(v) for k, v in self.word_counts.items()},
            "total_words_per_class": dict(self.total_words_per_class),
            "vocab": list(self.vocab),
            "total_docs": self.total_docs
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def load(cls, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        clf = cls()
        clf.class_counts = defaultdict(int, data["class_counts"])
        clf.word_counts = defaultdict(lambda: defaultdict(int), {k: defaultdict(int, v) for k, v in data["word_counts"].items()})
        clf.total_words_per_class = defaultdict(int, data["total_words_per_class"])
        clf.vocab = set(data["vocab"])
        clf.total_docs = data["total_docs"]
        return clf

_CAT_MODEL = None
_PRIO_MODEL = None

def get_models(models_dir="models"):
    global _CAT_MODEL, _PRIO_MODEL
    cat_path = Path(models_dir) / "category_model.json"
    prio_path = Path(models_dir) / "priority_model.json"

    if _CAT_MODEL is None and cat_path.exists():
        _CAT_MODEL = NaiveBayesClassifier.load(cat_path)

    if _PRIO_MODEL is None and prio_path.exists():
        _PRIO_MODEL = NaiveBayesClassifier.load(prio_path)

    return _CAT_MODEL, _PRIO_MODEL

def predict_email(subject, body, sender=""):
    cat_model, prio_model = get_models()
    if not cat_model or not prio_model:
        raise RuntimeError("Models are not trained yet. Run ml/train.py first.")

    text = f"{sender} {subject} {body}"
    cat, cat_conf, cat_probs = cat_model.predict_one(text)
    prio, prio_conf, prio_probs = prio_model.predict_one(text)

    return {
        "category": cat,
        "category_confidence": cat_conf,
        "category_probabilities": cat_probs,
        "priority": prio,
        "priority_confidence": prio_conf,
        "priority_probabilities": prio_probs
    }
