# Run it with GPU takes 0 minutes 

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
import json
from sentence_transformers import CrossEncoder, InputExample
from torch.utils.data import DataLoader

# ── Config ─────────────────────────────────────────────────────
TRAIN_PATH  = r"/kaggle/input/datasets/aaryaupi/training-json/train_split.json"
MODEL_OUT   = r"/kaggle/input/datasets/aaryaupi/training-json/test_split.json"

BASE_MODEL  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EPOCHS      = 3
BATCH_SIZE  = 16
LR          = 2e-5

def build_training_examples(train_records):
    """Convert verified chains into cross-encoder training pairs."""
    examples = []
    
    for r in train_records:
        query    = r["query"]
        q_final  = r["q_final"]
        gold_set = set(r["gold_titles"])
        
        for c in r["titles_and_first_sentence"]:
            is_gold      = c["title"] in gold_set
            candidate_tx = f"{c['title']} — {c['first_sentence']}"
            
            # Soft labels weighted by record quality
            if is_gold:
                label = q_final            # high-quality gold gets strong positive signal
            else:
                label = 0.1 * (1.0 - q_final)  # distractors weakly negative
            
            examples.append(InputExample(
                texts=[query, candidate_tx],
                label=float(label)
            ))
    
    print(f"[examples] Built {len(examples)} training pairs from {len(train_records)} records")
    return examples



