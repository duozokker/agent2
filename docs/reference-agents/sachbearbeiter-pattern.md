# Sachbearbeiter Reference Pattern

The Sachbearbeiter pattern is the production reference behind Agent2's Brain
Clone approach. It models a professional case worker: one experienced operator
handles one complete case from intake through review, communication, and final
typed output.

The original implementation works in the German accounting domain. Do not copy
the accounting details into unrelated agents. Copy the architecture.

## What It Proves

The pattern works because the agent is not treated as a deterministic workflow
engine. It is treated as an experienced professional sitting at a desk with the
same resources a human would use:

- document reader or OCR
- reference books and regulations
- client file
- vendor or entity file
- case history
- notepad or persistent memory
- communication channel
- sandboxed write actions

## Prompt Structure

The prompt has five functional layers:

1. Identity and mindset: an experienced professional who is careful, efficient,
   and never guesses.
2. Workspace: books, files, history, memory, web fallback, and communication
   tools described as items on the desk.
3. Work process: what the professional checks first, when they look things up,
   when they ask, when they reject, and when they complete.
4. Example cases: short narratives that demonstrate judgment paths without
   becoming hardcoded rules.
5. Three outcomes: complete, needs clarification, or rejected.

## Books, Not Code

The strongest principle is:

```text
The agent learns from books, not from code.
```

For accounting this means account mappings, tax keys, and formal requirements
belong in knowledge packages, not hidden Python lookup tools. For another domain
it means the same thing: policies, manuals, regulations, standards, and
reference tables belong in R2R collections.

When the agent makes a wrong expert decision, fix the source material, chunking,
prompt guidance, or eval coverage before adding deterministic domain shortcuts.

## Tools

The tool layer mirrors a professional workspace:

- `search()` / `get_passage()` for books
- `get_client_info()` or equivalent for the case file
- `lookup_entity()` / `list_entities()` for known vendors, suppliers, customers,
  contracts, or providers
- `get_case_history()` for previous similar work
- `update_*_memory()` for durable notes
- `web_search()` as fallback for current or missing public context
- sandbox communication tools for questions
- sandbox write tools for records that require approval

Tool names are domain language. Generic names make the model behave generically.

## Runtime Hooks

`before_run()` is responsible for:

- selecting active knowledge collections for the current case
- rendering dynamic prompt sections
- injecting `_instructions`
- detecting `message_history` resume
- validating prerequisites such as OCR availability
- creating fresh per-run MCP toolsets through `_toolsets`

Fresh MCP toolsets matter because shared MCP client instances can collide under
concurrent async runs. Agent2 supports this pattern by passing `_toolsets` from
`before_run()` into `Agent.run(toolsets=...)`.

`after_run()` is responsible for:

- persisting the final result
- storing `_message_history`
- appending communication thread entries
- flagging low-confidence results for human review
- surfacing persistence failures clearly

## Schema

The schema makes the prompt operational. The top-level result should include:

- a status literal with exactly three outcomes
- domain output for completed work
- clarification message for clarification cases
- rejection reason for rejected cases
- extracted fields
- confidence
- concise reasoning
- review steps
- pending actions

Use `model_validator` to enforce mutual exclusivity. The LLM should get a retry
instead of silently returning contradictory state.

## Evals

The Sachbearbeiter pattern is evaluated with behavior-level cases, not only JSON
shape checks. Evals ask whether the agent:

- chooses the right outcome
- asks when facts are missing
- rejects incurable defects
- uses the correct knowledge context
- formats the final work product correctly

Every serious Agent2 example should follow that standard.

## In-Repo Public Analogue

For a public, non-accounting example of the same pattern, study
[`agents/procurement-compliance-officer`](../../agents/procurement-compliance-officer).
It uses procurement policy books and vendor-risk books instead of accounting
books, but the architecture is the same.
