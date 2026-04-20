# Utils llm server abstraction

## Problem
Assistant endpoint uses static responses and lacks an LLM layer.

## Potentially Related Files
- [assistant.controller.ts](../apps/api/src/modules/disaster-response/assistant/assistant.controller.ts) - inquiry endpoint
- [assistant.provider.ts](../apps/api/src/modules/disaster-response/assistant/assistant.provider.ts) - provider interface
- [simple-assistant.provider.ts](../apps/api/src/modules/disaster-response/assistant/simple-assistant.provider.ts) - stub

## What to Fix
1. Implement pluggable provider adapter with config-driven provider selection
2. Add context assembly from active warnings, hazard pins, and location signals
3. Add timeout and fallback for provider failures
4. Regenerate API client if contract changes

## Acceptance Criteria
- Assistant uses configured provider through abstraction layer
- Response includes context-aware disaster guidance
- Provider failure returns safe fallback without server crash
