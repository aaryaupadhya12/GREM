from datasets import load_dataset

def load_hotpotqa():
    # distractor — this is the right choice
    ds = load_dataset("hotpotqa/hotpot_qa", "distractor")
    
    train = ds["train"]       # 90,447
    dev   = ds["validation"]  # 7,405
    
    print(f"Train: {len(train)}  Dev: {len(dev)}")
    return train, dev

train_ds, dev_ds = load_hotpotqa()

# What one record looks like after loading
sample = dev_ds[0]
print("Question:",   sample["question"])
print("Answer:",     sample["answer"])
print("Type:",       sample["type"])    # "bridge" or "comparison"
print("Level:",      sample["level"])   # "easy", "medium", "hard"
print("Gold titles", sample["supporting_facts"]["title"])
print("Context titles:", sample["context"]["title"])   # 10 titles
print("Num passages:",   len(sample["context"]["title"]))  # always 10