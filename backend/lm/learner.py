import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import numpy as np
from scipy.stats import mode as scipy_mode
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, fbeta_score, classification_report
)
from sklearn.preprocessing import StandardScaler
from sentence_transformers import SentenceTransformer

import time
import json
from datetime import datetime
import joblib

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

from google.colab import drive
drive.mount('/content/drive')

# Paths — adjust to match your Colab file locations
DATA_DIR = Path("pan2012")
TRAIN_XML       = DATA_DIR / "train" / "pan12-sexual-predator-identification-training-corpus-2012-05-01.xml"
TRAIN_PRED_TXT  = DATA_DIR / "train" / "pan12-sexual-predator-identification-training-corpus-predators-2012-05-01.txt"
TEST_XML        = DATA_DIR / "test"  / "pan12-sexual-predator-identification-test-corpus-2012-05-17.xml"
TEST_PRED_TXT   = DATA_DIR / "test"  / "pan12-sexual-predator-identification-groundtruth-problem1.txt"

# Checkpoint directory — embeddings and trained classifiers are cached here
CHECKPOINT_DIR = Path("/content/drive/MyDrive/grooming_detection/checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# SimCSE model names (all publicly available on HuggingFace via sentence-transformers)
SIMCSE_MODELS: Dict[str, str] = {
    "SimCSE-Base-Bert":    "princeton-nlp/sup-simcse-bert-base-uncased",
    "SimCSE-Large-Bert":   "princeton-nlp/sup-simcse-bert-large-uncased",
    "SimCSE-Base-RoBERTa": "princeton-nlp/sup-simcse-roberta-base",
    "SimCSE-Large-RoBERTa":"princeton-nlp/sup-simcse-roberta-large",
}

# Preprocessing thresholds (Section 3.1 of the paper)
MIN_MESSAGES   = 7   # conversations with fewer messages are discarded
MIN_AUTHORS    = 2   # conversations need exactly 2 authors
MAX_AUTHORS    = 2
RANDOM_STATE   = 42
BATCH_SIZE     = 64  # adjust down if GPU OOM

# ─────────────────────────────────────────────────────────────────────────────
# 2. CHECKPOINT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _emb_cache_path(split: str, emb_key: str) -> Path:
    """Return path for cached numpy embeddings."""
    safe_key = emb_key.replace(" ", "_").replace("/", "-")
    return CHECKPOINT_DIR / f"embeddings_{split}_{safe_key}.npy"


def _clf_cache_path(emb_key: str, clf_key: str) -> Path:
    """Return path for a cached (scaler, clf) joblib bundle."""
    safe = emb_key.replace(" ", "_").replace("/", "-")
    return CHECKPOINT_DIR / f"clf_{safe}_{clf_key}.joblib"


def _meta_path() -> Path:
    return CHECKPOINT_DIR / "run_meta.json"


def save_embeddings(split: str, emb_key: str, embeddings: np.ndarray) -> None:
    path = _emb_cache_path(split, emb_key)
    np.save(path, embeddings)
    print(f"  [ckpt] Saved {split} embeddings → {path}")


def load_embeddings(split: str, emb_key: str) -> Optional[np.ndarray]:
    path = _emb_cache_path(split, emb_key)
    if path.exists():
        arr = np.load(path)
        print(f"  [ckpt] Loaded {split} embeddings from cache ({arr.shape})")
        return arr
    return None


def save_classifier(emb_key: str, clf_key: str,
                    scaler: StandardScaler, clf) -> None:
    path = _clf_cache_path(emb_key, clf_key)
    joblib.dump({"scaler": scaler, "clf": clf}, path)
    print(f"  [ckpt] Saved classifier → {path}")


def load_classifier(emb_key: str, clf_key: str) -> Optional[Tuple]:
    path = _clf_cache_path(emb_key, clf_key)
    if path.exists():
        bundle = joblib.load(path)
        print(f"  [ckpt] Loaded classifier from cache: {emb_key} + {clf_key}")
        return bundle["scaler"], bundle["clf"]
    return None


def save_run_meta(meta: dict) -> None:
    with open(_meta_path(), "w") as f:
        json.dump(meta, f, indent=2)


def load_run_meta() -> dict:
    if _meta_path().exists():
        with open(_meta_path()) as f:
            return json.load(f)
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA LOADING & PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────

# Load predator IDs — try .txt first, fall back to .xml ground-truth
def load_preds(txt_path: Path) -> set:
    if txt_path.exists():
        return load_predator_ids(txt_path)
    xml_path = txt_path.with_suffix(".xml")
    if xml_path.exists():
        return load_predator_ids_from_xml(xml_path)
    raise FileNotFoundError(
        f"Cannot find predator ID file at {txt_path} or {xml_path}"
    )

def load_predator_ids(path: Path) -> set:
    """Load the set of known predator author-IDs from a plain-text file."""
    predators = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pid = line.strip()
            if pid:
                predators.add(pid)
    print(f"  Loaded {len(predators):,} predator IDs from {path.name}")
    return predators


def load_predator_ids_from_xml(path: Path) -> set:
    """
    Alternative: load predator IDs from the ground-truth XML used in some
    PAN 2012 test-set distributions.
    <users><user id="..."/></users>
    """
    tree = ET.parse(path)
    root = tree.getroot()
    return {u.get("id") for u in root.iter("user") if u.get("id")}


def is_english(text: str) -> bool:
    """Rough English-language filter: >80 % of chars are ASCII."""
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return ascii_count / len(text) > 0.80


def clean_text(text: str) -> str:
    """
    Light cleaning per Section 3.1:
      - no stemming / lemmatisation (preserve subword information)
      - remove non-English tokens (words) but keep punctuation
    """
    # Remove XML-escaped artifacts
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    # Keep words that are mostly ASCII; drop fully non-ASCII tokens
    tokens = text.split()
    filtered = []
    for tok in tokens:
        ascii_ratio = sum(1 for c in tok if ord(c) < 128) / max(len(tok), 1)
        if ascii_ratio >= 0.70:
            filtered.append(tok)
    return " ".join(filtered).strip()


def load_conversations(xml_path: Path, predator_ids: set) -> Tuple[List[str], List[int]]:
    """
    Parse the PAN 2012 XML corpus and return (texts, labels).

    XML structure:
        <conversations>
          <conversation id="...">
            <message line="1">
              <author>...</author>
              <time>...</time>
              <text>...</text>
            </message>
            ...
          </conversation>
        </conversations>

    Labelling rule (Section 3.1):
        If ANY author in a conversation is in predator_ids → label = 1 (predatory)
        Otherwise → label = 0 (non-predatory)

    Filtering rules:
        - Discard conversations with < MIN_MESSAGES messages
        - Discard conversations with != 2 unique authors
        - Remove non-English content
    """
    print(f"  Parsing {xml_path} …")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    texts, labels = [], []
    total = skipped_msg = skipped_authors = skipped_english = 0

    for conv in root.iter("conversation"):
        total += 1
        messages = list(conv.iter("message"))

        # Filter: too few messages
        if len(messages) < MIN_MESSAGES:
            skipped_msg += 1
            continue

        # Collect authors
        authors = {m.find("author").text.strip()
                   for m in messages
                   if m.find("author") is not None and m.find("author").text}

        # Filter: not exactly 2 authors
        if not (MIN_AUTHORS <= len(authors) <= MAX_AUTHORS):
            skipped_authors += 1
            continue

        # Merge all message texts into one document
        raw_parts = []
        for m in messages:
            t = m.find("text")
            if t is not None and t.text:
                raw_parts.append(t.text.strip())
        full_text = " ".join(raw_parts)
        cleaned   = clean_text(full_text)

        # Filter: not English enough
        if not is_english(cleaned) or len(cleaned) < 10:
            skipped_english += 1
            continue

        # Label
        label = 1 if authors & predator_ids else 0
        texts.append(cleaned)
        labels.append(label)

    print(f"    Total conversations : {total:,}")
    print(f"    Skipped (<{MIN_MESSAGES} msgs)   : {skipped_msg:,}")
    print(f"    Skipped (authors≠2) : {skipped_authors:,}")
    print(f"    Skipped (non-EN)    : {skipped_english:,}")
    print(f"    Kept → {len(texts):,}  "
          f"(predatory={sum(labels):,}, non-predatory={len(labels)-sum(labels):,})")
    return texts, labels


# ─────────────────────────────────────────────────────────────────────────────
# 4. SIMCSE SENTENCE EMBEDDINGS
# ─────────────────────────────────────────────────────────────────────────────

def get_embeddings(emb_key, model_name, split, texts,
                   device="cuda", force_recompute=False,
                   batch_size=BATCH_SIZE):
    """
    Return embeddings for `texts`, loading from cache when available.

    Args:
        emb_key:         Short name used as the cache key (e.g. "SimCSE-Base-Bert")
        model_name:      HuggingFace model path
        split:           "train" or "test"
        texts:           List of raw text strings to encode
        device:          "cuda" or "cpu"
        force_recompute: If True, ignore any existing cache and re-encode
    """
    if not force_recompute:
        cached = load_embeddings(split, emb_key)
        if cached is not None:
            return cached

    print(f"  Loading model: {model_name}")
    model = SentenceTransformer(model_name, device=device)
    print(f"  Encoding {len(texts):,} {split} texts …")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    print(f"  Embedding shape: {embeddings.shape}")

    save_embeddings(split, emb_key, embeddings)
    return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# 5. CLASSIFIERS
# ─────────────────────────────────────────────────────────────────────────────

def build_classifiers() -> Dict[str, object]:
    """Return the four classifier variants used in the paper."""
    return {
        "SVM": SVC(
            kernel="rbf",
            C=1.0,
            probability=True,   # needed for score-level fusion
            random_state=RANDOM_STATE,
            class_weight="balanced",
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=-1,
        ),
        "NaiveBayes": GaussianNB(),
        "SGD": SGDClassifier(
            loss="modified_huber",  # supports predict_proba
            random_state=RANDOM_STATE,
            class_weight="balanced",
            n_jobs=-1,
        ),
    }


def train_and_predict(
    X_train: np.ndarray,
    y_train: List[int],
    X_test: np.ndarray,
    emb_key: str,
    clf_key: str,
    clf,
    force_retrain: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Scale → fit → predict, with checkpoint save/load.

    If a saved (scaler, clf) bundle exists and force_retrain=False,
    the bundle is loaded and only inference is run.
    """
    if not force_retrain:
        bundle = load_classifier(emb_key, clf_key)
        if bundle is not None:
            scaler, clf = bundle
            X_te = scaler.transform(X_test)
            preds  = clf.predict(X_te)
            probas = clf.predict_proba(X_te)[:, 1]
            return preds, probas

    # Fresh training
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)

    clf.fit(X_tr, y_train)
    preds  = clf.predict(X_te)
    probas = clf.predict_proba(X_te)[:, 1]

    save_classifier(emb_key, clf_key, scaler, clf)
    return preds, probas


# ─────────────────────────────────────────────────────────────────────────────
# 6. METRICS
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(y_true: List[int], y_pred: np.ndarray,
             label: str = "") -> Dict[str, float]:
    """Compute Accuracy, Precision, Recall, F1, F0.5."""
    acc  = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec  = recall_score(y_true, y_pred, zero_division=0)
    f1   = f1_score(y_true, y_pred, zero_division=0)
    f05  = fbeta_score(y_true, y_pred, beta=0.5, zero_division=0)

    if label:
        print(f"\n{'─'*55}")
        print(f"  {label}")
        print(f"{'─'*55}")
        print(f"  Accuracy  : {acc:.4f}")
        print(f"  Precision : {prec:.4f}")
        print(f"  Recall    : {rec:.4f}")
        print(f"  F1        : {f1:.4f}")
        print(f"  F0.5      : {f05:.4f}")

    return dict(accuracy=acc, precision=prec, recall=rec, f1=f1, f05=f05)


# ─────────────────────────────────────────────────────────────────────────────
# 7. FUSION STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────

def sum_rule_fusion(score_list: List[np.ndarray]) -> np.ndarray:
    """Score-level sum fusion (Eq. 8 in the paper)."""
    return np.sum(score_list, axis=0)


def product_rule_fusion(score_list: List[np.ndarray]) -> np.ndarray:
    """Score-level product fusion (Eq. 9)."""
    result = np.ones(len(score_list[0]))
    for s in score_list:
        result *= s
    return result


def majority_voting_fusion(decision_list: List[np.ndarray]) -> np.ndarray:
    """Decision-level majority voting (Eq. 10)."""
    stack = np.stack(decision_list, axis=1)   # (N, K)
    voted, _ = scipy_mode(stack, axis=1)
    return voted.flatten().astype(int)


def scores_to_labels(scores: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Convert probability scores to binary labels."""
    # When scores are sums/products they are not bounded to [0,1];
    # we threshold at the midpoint of the actual range.
    mid = (scores.max() + scores.min()) / 2
    return (scores >= mid).astype(int)


# ─────────────────────────────────────────────────────────────────────────────
# 8. FULL PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    device: str = "cuda",
    force_recompute_embeddings: bool = False,
    force_retrain_classifiers: bool = False,
):
    """
    End-to-end execution of the paper's full pipeline.

    Steps:
      A) Load & preprocess PAN 2012 data
      B) For each of 4 SimCSE embeddings:
           - Encode train / test
           - Train 4 classifiers
           - Collect predictions & probability scores
      C) Evaluate each (embedding × classifier) combination
      D) Apply score-level and decision-level fusion across classifiers
         per embedding (Table 4 in the paper)
      E) Apply fusion across ALL 16 (embedding × classifier) combinations
         (Table 5 in the paper)

    Flags:
        force_recompute_embeddings  — ignore cached .npy files and re-encode
        force_retrain_classifiers   — ignore cached .joblib files and re-train
    """
    run_meta = load_run_meta()
    run_start = datetime.now().isoformat()
    print(f"\nRun started: {run_start}")

    # ── A. Data ──────────────────────────────────────────────────────────────
    print("\n" + "═"*60)
    print("  STEP 1 — Loading PAN 2012 dataset")
    print("═"*60)

    print("\n[Train]")
    train_preds = load_preds(TRAIN_PRED_TXT)
    train_texts, train_labels = load_conversations(TRAIN_XML, train_preds)

    print("\n[Test]")
    test_preds = load_preds(TEST_PRED_TXT)
    test_texts, test_labels  = load_conversations(TEST_XML, test_preds)

    y_train = np.array(train_labels)
    y_test  = np.array(test_labels)

    # ── B & C. Embeddings + Classifiers ──────────────────────────────────────
    print("\n" + "═"*60)
    print("  STEP 2 — Extracting embeddings & training classifiers")
    print("═"*60)

    # Storage for fusion
    # all_probas[emb_key][clf_key] = np.ndarray of shape (N_test,)
    # all_preds [emb_key][clf_key] = np.ndarray of shape (N_test,)
    all_probas: Dict[str, Dict[str, np.ndarray]] = {}
    all_preds:  Dict[str, Dict[str, np.ndarray]] = {}
    all_results: Dict[str, Dict[str, Dict]] = {}

    for emb_key, model_name in SIMCSE_MODELS.items():
        print(f"\n{'━'*60}")
        print(f"  Embedding: {emb_key}")
        print(f"{'━'*60}")

        X_train = get_embeddings(
            emb_key, model_name, "train", train_texts,
            device=device, force_recompute=force_recompute_embeddings,
        )
        X_test = get_embeddings(
            emb_key, model_name, "test", test_texts,
            device=device, force_recompute=force_recompute_embeddings,
        )

        all_probas[emb_key]  = {}
        all_preds[emb_key]   = {}
        all_results[emb_key] = {}

        for clf_key, clf in build_classifiers().items():
            print(f"\n  → Classifier: {clf_key}")
            t0 = time.time()
            preds, probas = train_and_predict(
                X_train, y_train, X_test,
                emb_key, clf_key, clf,
                force_retrain=force_retrain_classifiers,
            )
            elapsed = time.time() - t0

            all_preds[emb_key][clf_key]  = preds
            all_probas[emb_key][clf_key] = probas

            label  = f"{emb_key} + {clf_key}"
            result = evaluate(y_test, preds, label=label)
            result["train_time_s"] = round(elapsed, 2)
            all_results[emb_key][clf_key] = result

            # ── per-(emb, clf) checkpoint ─────────────────────────────────
            run_meta[f"{emb_key}_{clf_key}"] = {
                "completed": True,
                "timestamp": datetime.now().isoformat(),
                **{k: v for k, v in result.items() if k != "train_time_s"},
            }
            save_run_meta(run_meta)


    # ── D. Fusion per embedding (Table 4) ────────────────────────────────────
    print("\n" + "═"*60)
    print("  STEP 3 — Fusion per embedding (Table 4)")
    print("═"*60)

    per_emb_fusion_results: Dict[str, Dict[str, Dict]] = {}

    for emb_key in SIMCSE_MODELS:
        per_emb_fusion_results[emb_key] = {}
        clf_keys = list(all_probas[emb_key].keys())

        score_list    = [all_probas[emb_key][k] for k in clf_keys]
        decision_list = [all_preds[emb_key][k]  for k in clf_keys]

        # Sum
        sum_scores  = sum_rule_fusion(score_list)
        sum_labels  = scores_to_labels(sum_scores)
        r = evaluate(y_test, sum_labels, label=f"{emb_key} | Sum Fusion")
        per_emb_fusion_results[emb_key]["Sum"] = r

        # Product
        prod_scores = product_rule_fusion(score_list)
        prod_labels = scores_to_labels(prod_scores)
        r = evaluate(y_test, prod_labels, label=f"{emb_key} | Product Fusion")
        per_emb_fusion_results[emb_key]["Product"] = r

        # Majority voting
        maj_labels = majority_voting_fusion(decision_list)
        r = evaluate(y_test, maj_labels, label=f"{emb_key} | Majority Voting")
        per_emb_fusion_results[emb_key]["Majority"] = r

    # ── E. Fusion across all 16 combinations (Table 5) ───────────────────────
    print("\n" + "═"*60)
    print("  STEP 4 — Fusion of all 16 configurations (Table 5)")
    print("═"*60)

    all_score_list    = []
    all_decision_list = []
    for emb_key in SIMCSE_MODELS:
        for clf_key in all_probas[emb_key]:
            all_score_list.append(all_probas[emb_key][clf_key])
            all_decision_list.append(all_preds[emb_key][clf_key])

    global_sum_labels     = scores_to_labels(sum_rule_fusion(all_score_list))
    global_product_labels = scores_to_labels(product_rule_fusion(all_score_list))
    global_majority_labels = majority_voting_fusion(all_decision_list)

    global_results = {}
    global_results["Sum"]      = evaluate(y_test, global_sum_labels,
                                           label="ALL configurations | Sum Rule")
    global_results["Product"]  = evaluate(y_test, global_product_labels,
                                           label="ALL configurations | Product Rule")
    global_results["Majority"] = evaluate(y_test, global_majority_labels,
                                           label="ALL configurations | Majority Voting")

    # ── Final summary ─────────────────────────────────────────────────────────
    run_meta["run_start"]    = run_start
    run_meta["run_end"]      = datetime.now().isoformat()
    run_meta["global_fusion"] = global_results

    save_run_meta(run_meta)
    _print_summary(all_results, per_emb_fusion_results, global_results)

    return {
        "per_model_per_clf": all_results,
        "per_model_fusion":  per_emb_fusion_results,
        "global_fusion":     global_results,
    }

# ─────────────────────────────────────────────────────────────────────────────
# 9. SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(per_model_per_clf, per_model_fusion, global_results):
    header = f"{'Config':<42} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'F0.5':>6}"
    sep    = "─" * len(header)

    print("\n\n" + "═"*len(header))
    print("  RESULTS SUMMARY")
    print("═"*len(header))

    print(f"\n{'Single Classifier Results':^{len(header)}}")
    print(sep); print(header); print(sep)
    for emb, clf_dict in per_model_per_clf.items():
        for clf, m in clf_dict.items():
            print(f"{emb+' + '+clf:<42} {m['accuracy']:>6.4f} {m['precision']:>6.4f} "
                  f"{m['recall']:>6.4f} {m['f1']:>6.4f} {m['f05']:>6.4f}")

    print(f"\n{'Per-Embedding Fusion Results':^{len(header)}}")
    print(sep); print(header); print(sep)
    for emb, fuse_dict in per_model_fusion.items():
        for ftype, m in fuse_dict.items():
            print(f"{emb+' | '+ftype:<42} {m['accuracy']:>6.4f} {m['precision']:>6.4f} "
                  f"{m['recall']:>6.4f} {m['f1']:>6.4f} {m['f05']:>6.4f}")

    print(f"\n{'Global Fusion Results (all 16 configs)':^{len(header)}}")
    print(sep); print(header); print(sep)
    for ftype, m in global_results.items():
        print(f"{'All configs | '+ftype:<42} {m['accuracy']:>6.4f} {m['precision']:>6.4f} "
              f"{m['recall']:>6.4f} {m['f1']:>6.4f} {m['f05']:>6.4f}")
    print(sep + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# 10. QUICK DEMO WITH SYNTHETIC DATA
# ─────────────────────────────────────────────────────────────────────────────

def run_demo(device: str = "cpu"):
    """Smoke-test with 50 synthetic sentences — no PAN 2012 data needed."""
    print("\n" + "═"*60)
    print("  DEMO MODE  (synthetic data, SimCSE-Base-RoBERTa + SVM)")
    print("═"*60)

    import random
    random.seed(42)

    predatory  = [
        "hey can we keep this just between us ok",
        "you seem really mature for your age",
        "do you have a camera on your phone",
        "lets meet up sometime when your parents arent home",
        "i bought you a gift do you want it",
    ]
    normal = [
        "what did you think of the homework assignment",
        "the match yesterday was amazing did you watch it",
        "can you recommend a good movie to watch",
        "i am going to the library to study",
        "lets meet at the park with the whole group",
    ]

    def make(templates, n):
        return [random.choice(templates) + " " + random.choice(templates)
                for _ in range(n)]

    n = 25
    train_texts  = make(predatory, n) + make(normal, n)
    train_labels = [1]*n + [0]*n
    test_texts   = make(predatory, n) + make(normal, n)
    test_labels  = [1]*n + [0]*n

    emb_key    = "SimCSE-Base-RoBERTa"
    model_name = SIMCSE_MODELS[emb_key]

    X_train = get_embeddings(emb_key, model_name, "demo_train", train_texts,
                              batch_size=16, device=device)
    X_test  = get_embeddings(emb_key, model_name, "demo_test",  test_texts,
                              batch_size=16, device=device)

    clf = SVC(kernel="rbf", probability=True,
              random_state=42, class_weight="balanced")
    preds, _ = train_and_predict(
        X_train, train_labels, X_test,
        emb_key, "SVM_demo", clf,
    )
    evaluate(np.array(test_labels), preds,
             label="Demo: SimCSE-Base-RoBERTa + SVM")
    print("\nDemo finished. Run run_pipeline() with PAN 2012 data next.\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    print(f"Checkpoint directory: {CHECKPOINT_DIR.resolve()}")

    # ── Option A: resume / full pipeline ──────────────────────────────────────
    results = run_pipeline(
        device=device,
        force_recompute_embeddings=False,   # set True to re-encode from scratch
        force_retrain_classifiers=False,    # set True to ignore .joblib cache
    )

    print(results)

    # ── Option B: quick smoke-test ────────────────────────────────────────────
    # run_demo(device=device)
