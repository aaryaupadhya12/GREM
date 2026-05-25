# DISTRACTOR 

## Why we use the DISTRACTOR version than the Full Wiki dataset

Each question comes with exactly 10 paragraphs
2 Golden paragraphs (context relevance)
8 distractors 

BM25 as a Baseline is ran on this dataset to see on what subset of the training data it fails on 

Distractor distractors are HAND-CRAFTED hard negatives.
They were specifically chosen by the HotpotQA authors to fool retrieval systems.

That means:
  BM25 fails because the distractor passage uses
  the same entities as the gold passage but in
  wrong relational context.

  EXACTLY the failure mode our bridge entity reasoning was built to fix.

The Fail rate was -- 

FULL WIKI Dataset Subset 

Open dpomain retrical of all wikipedia 
Millions of passages and Buidlign retrical indexes ourselves

For the Vendor We are working with MongoDB the M0 free tier allows 512 MB storage across both the inference and the training pipeline to store the data nad hence we dont use Fullwiki as a engineering choice 