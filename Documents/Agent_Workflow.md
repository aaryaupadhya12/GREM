# Prompting Strategy for Agents A, B, C and Aggregator

Our system uses a multi-agent prompting architecture inspired by structured reasoning and retrieval-augmented workflows.

Each agent receives:
- its local task instructions
- a shared global `Context.md` file describing the overall system objective and output structure

This allows agents to optimize both for immediate subtasks and the broader retrieval/distillation pipeline.

---

## Context Compression and Memory Efficiency

To prevent context overflow and reduce memory usage, intermediate reasoning traces are compressed into structured summaries before being passed between agents.

This adaptive summarization approach:
- reduces token growth
- enables scalable multi-agent interaction
- fits within MongoDB M0 storage limitations and API context constraints

---

## Aggregator Design

The aggregator agent:
- combines reasoning summaries from Agents A, B, and C
- validates structural consistency
- prepares outputs for downstream distillation tasks

This aggregation layer also helps preserve reasoning alignment across the pipeline while maintaining bounded memory usage.

---

## Gemini API Optimization

Since the system operates entirely through hosted APIs rather than local model weights, optimization is performed through inference-time controls such as:
- `max_output_tokens`
- `top_k`
- `top_p`
- `stop_sequences`

These controls help maintain:
- deterministic formatting
- bounded outputs
- lower token usage
- improved response consistency

According to Google's documentation, a token is approximately four characters, and 100 tokens roughly correspond to 60–80 words.

Source: https://ai.google.dev/gemini-api/docs/prompting-strategies

---

## Structured Prompt Engineering

Prompts are written using structured Markdown formatting to improve:
- instruction separation
- role clarity
- output consistency
- parsing reliability

Each agent follows a constrained output structure to ensure downstream compatibility with the aggregator and distillation stages.

---

## Agent Workflow Design

The system follows a sequential multi-agent workflow:
1. Specialized agents process retrieval and reasoning subtasks
2. Intermediate outputs are summarized and compressed
3. The aggregator merges and validates reasoning traces
4. Final outputs are prepared for ranking/distillation tasks

This design helps maintain scalability while reducing context-window overflow during long reasoning chains.