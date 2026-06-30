import joblib
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CHECKPOINT_DIR = Path("/content/drive/MyDrive/grooming_detection/checkpoints")

EMB_KEY = "SimCSE-Base-Bert"
MODEL_NAME = "princeton-nlp/sup-simcse-bert-base-uncased"
CLF_KEY = "SVM"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA PREPROCESSING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────


def clean_text(text: str) -> str:
    """Light cleaning matching Section 3.1 of the pipeline."""
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    tokens = text.split()
    filtered = []
    for tok in tokens:
        ascii_ratio = sum(1 for c in tok if ord(c) < 128) / max(len(tok), 1)
        if ascii_ratio >= 0.70:
            filtered.append(tok)
    return " ".join(filtered).strip()

# ─────────────────────────────────────────────────────────────────────────────
# 3. INFERENCE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_conversation_inference(list_of_conversations: list):
    """
    Accepts a list where each element is a LIST of messages (strings) representing
    a complete chat log. Joins the messages, cleans them, and returns predictions.
    """
    safe_emb_key = EMB_KEY.replace(" ", "_").replace("/", "-")
    model_path = CHECKPOINT_DIR / f"clf_{safe_emb_key}_{CLF_KEY}.joblib"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Could not find saved model at: {model_path}")
        
    print(f"Loading classifier bundle from: {model_path.name}")
    bundle = joblib.load(model_path)
    scaler = bundle["scaler"]
    clf = bundle["clf"]

    # Step 1: Combine the separate messages of each conversation into a single block
    # This precisely mimics the "full_text = ' '.join(raw_parts)" from your training pipeline
    merged_conversations = []
    for chat_history in list_of_conversations:
        full_text = " ".join(chat_history)
        cleaned_text = clean_text(full_text)
        merged_conversations.append(cleaned_text)

    # Step 2: Load the exact matching encoder and embed text
    print(f"Loading embedding model: {MODEL_NAME} on {DEVICE}...")
    encoder = SentenceTransformer(MODEL_NAME, device=DEVICE)
    
    print("Generating sentence embeddings...")
    embeddings = encoder.encode(
        merged_conversations,
        batch_size=len(merged_conversations),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False
    )
    
    # Step 3: Scale features using the training pipeline's scaler
    X_scaled = scaler.transform(embeddings)
    
    # Step 4: Run inference
    print("Running classification...")
    predictions = clf.predict(X_scaled)
    probabilities = clf.predict_proba(X_scaled)[:, 1]
    
    return predictions, probabilities

# ─────────────────────────────────────────────────────────────────────────────
# 4. EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import torch
    
    # Each list here represents a SINGLE complete conversation session
    predatory_chat_session = [
        "hello there",
        "im just chilling online and looking for new people to talk to",
        "hey can we keep this just between us ok",
        "i feel like you understand me better than older people do",
        "you seem really mature for your age",
        "what do you look like anyway",
        "do you have a camera on your phone",
        "lets meet up sometime when your parents arent home",
        "i can drive over to your neighborhood this weekend",
        "i bought you a gift do you want it",
    ]
    
    normal_chat_session = [
        "hey what's up",
        "did you finish studying for the exam tomorrow",
        "what did you think of the homework assignment",
        "it was way too long but i think i got most of it right",
        "the match yesterday was amazing did you watch it",
        "yeah our team played so well in the second half",
        "can you recommend a good movie to watch tonight",
        "i am going to the library to study if you want to join",
        "sounds good i need to return some books anyway",
        "lets meet at the park with the whole group first",
    ]
    
    # We pack both full conversations into our test batch list
    all_test_sessions = [predatory_chat_session, normal_chat_session]
    
    # Run the combined model inference
    preds, scores = run_conversation_inference(all_test_sessions)
    
    print("\n" + "="*60)
    print("  INFERENCE RESULTS")
    print("="*60)
    
    # Process Conversation 1 (Suspicious Batch)
    label_1 = "[*] Flagged (Suspicious)" if preds[0] == 1 else "[+] Normal"
    print(f"[Conversation 1 - Suspicious Session]")
    print(f" Message Count : {len(predatory_chat_session)}")
    print(f" Decision      : {label_1}")
    print(f" Confidence    : {scores[0]:.4f}")
    
    # Process Conversation 2 (Normal Batch)
    print(f"\n{'─'*60}")
    label_2 = "[*] Flagged (Suspicious)" if preds[1] == 1 else "[+] Normal"
    print(f"[Conversation 2 - Normal Session]")
    print(f" Message Count : {len(normal_chat_session)}")
    print(f" Decision      : {label_2}")
    print(f" Confidence    : {scores[1]:.4f}")
    print("="*60 + "\n")
