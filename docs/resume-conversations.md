# Resume and Conversations

## Why the framework uses serialized message history

Conversation state should not be hidden inside one process. Products need to persist it, inspect it, and move it across containers.

That is why Agent2 exposes pause/resume through explicit message history data instead of a private in-memory session.

## Request contract

Send this on input:

```json
{
  "input": {
    "text": "Continue the analysis",
    "message_history": [...]
  }
}
```

Receive this on output:

```json
{
  "result": {
    "...": "...",
    "_message_history": [...]
  }
}
```

## Host responsibilities

The host should:

- persist `_message_history`
- decide when a run is resumed
- send the history back on the next turn
- optionally enrich the next run through `before_run()`

## Framework responsibilities

The framework will:

- deserialize `message_history`
- pass it into PydanticAI
- serialize the updated history back into `_message_history`
- keep the transport JSON-safe

## Example

See [`agents/resume-demo`](../agents/resume-demo) for a minimal implementation.
