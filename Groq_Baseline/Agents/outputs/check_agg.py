import json
from collections import Counter

with open(r'C:\Users\Aarya-2\Documents\ADOG\MARLOW AI\QGED_CODEX_M_L\GREM\Groq_Baseline\Agents\outputs\aggregator_out.json') as f:
    data = json.load(f)

scores = [r['q_final'] for r in data]
modes  = Counter(r['failure_mode'] for r in data)
mongo  = sum(1 for r in data if r['storage_route'] == 'mongodb')
ram    = sum(1 for r in data if r['storage_route'] == 'session_ram')

print(f"Total records   : {len(data)}")
print(f"Avg q_final     : {sum(scores)/len(scores):.3f}")
print(f"Min q_final     : {min(scores):.3f}")
print(f"Max q_final     : {max(scores):.3f}")
print(f"-> MongoDB      : {mongo}")
print(f"-> Session RAM  : {ram}")
print(f"\nFailure modes:")
for mode, count in modes.most_common():
    print(f"  {mode}: {count}")