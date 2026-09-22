import csv
import sys
import random
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from apps.services.classifier import NaiveBayesClassifier

def evaluate_metrics(y_true, y_pred, title):
    classes = sorted(list(set(y_true)))
    print("=" * 65)
    print(f"EVALUATION RESULTS: {title}")
    print("=" * 65)
    print(f"{'Class':<15} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}")
    print("-" * 65)

    precisions = []
    recalls = []
    f1s = []
    total_samples = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)

    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)
        support = sum(1 for yt in y_true if yt == c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

        print(f"{c:<15} {precision:<12.2%} {recall:<12.2%} {f1:<12.2%} {support:<8}")

    print("-" * 65)
    macro_prec = sum(precisions) / len(precisions)
    macro_rec = sum(recalls) / len(recalls)
    macro_f1 = sum(f1s) / len(f1s)
    accuracy = correct / total_samples

    print(f"{'Accuracy':<15} {'':<12} {'':<12} {accuracy:<12.2%} {total_samples:<8}")
    print(f"{'Macro Avg':<15} {macro_prec:<12.2%} {macro_rec:<12.2%} {macro_f1:<12.2%} {total_samples:<8}")
    print("=" * 65)

def train_and_evaluate():
    data_path = Path("data/email_dataset.csv")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    rows = []
    with open(data_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            sender = r.get("sender", "") or ""
            subject = r.get("subject", "") or ""
            snippet = r.get("body_snippet", "") or ""
            text = f"{sender} {subject} {snippet}"
            rows.append({
                "text": text,
                "category": r["category"],
                "priority": r["priority"]
            })

    random.seed(42)
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    train_data = []
    test_data = []

    for cat, items in by_cat.items():
        random.shuffle(items)
        split_idx = int(len(items) * 0.8)
        train_data.extend(items[:split_idx])
        test_data.extend(items[split_idx:])

    train_texts = [d["text"] for d in train_data]
    test_texts = [d["text"] for d in test_data]

    y_train_cat = [d["category"] for d in train_data]
    y_test_cat = [d["category"] for d in test_data]

    y_train_prio = [d["priority"] for d in train_data]
    y_test_prio = [d["priority"] for d in test_data]

    print(f"\nTraining set size: {len(train_data)} emails")
    print(f"Test set size:     {len(test_data)} unseen emails\n")

    cat_model = NaiveBayesClassifier()
    cat_model.fit(train_texts, y_train_cat)
    pred_cat = cat_model.predict(test_texts)
    evaluate_metrics(y_test_cat, pred_cat, "CATEGORY MODEL (20% UNSEEN TEST SET)")

    prio_model = NaiveBayesClassifier()
    prio_model.fit(train_texts, y_train_prio)
    pred_prio = prio_model.predict(test_texts)
    evaluate_metrics(y_test_prio, pred_prio, "PRIORITY MODEL (20% UNSEEN TEST SET)")

    cat_model.save(models_dir / "category_model.json")
    prio_model.save(models_dir / "priority_model.json")

    print(f"\nTrained models saved to:")
    print(f"  - {models_dir / 'category_model.json'}")
    print(f"  - {models_dir / 'priority_model.json'}\n")

if __name__ == "__main__":
    train_and_evaluate()
