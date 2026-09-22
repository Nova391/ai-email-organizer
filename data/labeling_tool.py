import sqlite3
import csv
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATASET_PATH = Path("data/email_dataset.csv")
HEADERS = ["gmail_id", "sender", "subject", "body_snippet", "category", "priority"]

CATEGORIES = {
    "1": "work",
    "2": "finance",
    "3": "alerts",
    "4": "promotions",
    "5": "updates",
    "6": "social",
    "7": "travel",
    "8": "education",
    "9": "personal",
    "10": "spam",
    "11": "other"
}

PRIORITIES = {
    "1": "high",
    "2": "medium",
    "3": "low"
}

def get_labeled_ids(csv_path=DATASET_PATH):
    labeled_ids = set()
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
        return labeled_ids

    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("gmail_id"):
                labeled_ids.add(row["gmail_id"])
    return labeled_ids

def get_emails():
    connection = sqlite3.connect("emails.db")
    cursor = connection.cursor()
    cursor.execute("SELECT gmail_id, sender, subject, body FROM emails")
    emails = cursor.fetchall()
    connection.close()
    return emails

def clean_snippet(text, max_len=250):
    if not text:
        return ""
    single_line = " ".join(text.split())
    if len(single_line) > max_len:
        return single_line[:max_len] + "..."
    return single_line

def label_emails():
    labeled_ids = get_labeled_ids()
    all_emails = get_emails()
    unlabeled = [e for e in all_emails if e[0] not in labeled_ids]
    
    total = len(all_emails)
    done = len(labeled_ids)
    remaining = len(unlabeled)

    if remaining == 0:
        print("All emails are already labeled!")
        return

    print(f"\nProgress: {done}/{total} completed ({remaining} remaining).\n")

    for idx, (gmail_id, sender, subject, body) in enumerate(unlabeled, start=1):
        snippet = clean_snippet(body)

        print("-" * 60)
        print(f"[{idx}/{remaining}] Email Details:")
        print(f"  From:    {sender or 'Unknown'}")
        print(f"  Subject: {subject or '(No Subject)'}")
        print(f"  Snippet: {snippet}")
        print("-" * 60)

        print("Categories:")
        for num, name in CATEGORIES.items():
            print(f"  [{num}] {name}")

        chosen_cat = None
        while not chosen_cat:
            cat_input = input("Choose category (1-11 or name, 'q' to quit): ").strip().lower()
            if cat_input == "q":
                print("\nSaved your progress. See you next time!")
                return
            if cat_input in CATEGORIES:
                chosen_cat = CATEGORIES[cat_input]
            elif cat_input in CATEGORIES.values():
                chosen_cat = cat_input
            else:
                print("Invalid choice. Please enter 1-11 or category name.")

        print("\nPriorities:")
        for num, name in PRIORITIES.items():
            print(f"  [{num}] {name}")

        chosen_prio = None
        while not chosen_prio:
            prio_input = input("Choose priority (1-3 or name, 'q' to quit): ").strip().lower()
            if prio_input == "q":
                print("\nSaved your progress. See you next time!")
                return
            if prio_input in PRIORITIES:
                chosen_prio = PRIORITIES[prio_input]
            elif prio_input in PRIORITIES.values():
                chosen_prio = prio_input
            else:
                print("Invalid choice. Please enter 1-3 or priority name.")

        with open(DATASET_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([gmail_id, sender, subject, snippet, chosen_cat, chosen_prio])

        print(f"\nSaved: {chosen_cat} | {chosen_prio}\n")

    print("All emails labeled successfully!")

if __name__ == "__main__":
    label_emails()