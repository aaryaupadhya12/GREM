"""
agent_a.py — Entity Overlap Reasoner
 
Usage:
    python agent_a.py
 
Reads:  outputs/subset.json
Writes: outputs/agent_a_out.json  (saves after every record)
 
Set your API key:
    export GROQ_API_KEY_A="gsk_..."
"""
 
import json
import os
import time
from groq import Groq



