# Provider Policy

## Why provider affinity matters

When a model family is available through multiple upstream providers, repeated requests can become much more expensive if traffic bounces between them.

The main example is prompt caching:

- one provider holds the warm cache
- the next request lands on another provider
- cache reads are lost
- cost and latency both spike

## Config shape

```yaml
provider_order:
  - anthropic
provider_policy:
  allow_fallbacks: true
```

## Framework behavior

`create_agent()` maps this into OpenRouter model settings when the selected model is routed through OpenRouter.

This gives products a framework-level control point for:

- provider affinity
- cache-aware routing
- fallback tolerance

## Failure handling

The API layer also classifies provider-auth failures and can fall back to safe mock responses in development-oriented scenarios instead of crashing with an opaque transport error.

## Example

See [`agents/provider-policy-demo`](../agents/provider-policy-demo).
