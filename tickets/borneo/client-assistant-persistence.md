# client-assistant-persistence.md

## Problem
Currently, the `LLMAssistant` chat history is stored in local component state. When a user navigates away to another screen (e.g., Map or Profile), the component unmounts and all messages are lost, forcing the user to restart the conversation.

## Potentially Related Files
- [LLMAssistant.tsx](../apps/mobile/src/components/screens/LLMAssistant.tsx#L7-L16) - Current local state implementation
- [Providers.tsx](../apps/mobile/src/components/Providers.tsx) - Suggested location for new Assistant context provider
- [MainApp.tsx](../apps/mobile/src/components/MainApp.tsx#L92) - Screen rendering logic where unmounting occurs

## What to Fix
1. Create a React Context (e.g., `AssistantContext.tsx`) to store the `messages` array and provide an `addMessage` function.
2. Initialize the context with the default welcome message from the assistant.
3. Wrap the mobile application with the new `AssistantProvider` in `Providers.tsx`.
4. Refactor `LLMAssistant.tsx` to consume messages from the context instead of local `useState`.
5. Update `handleSend` in `LLMAssistant.tsx` to push new messages to the context.

## Acceptance Criteria
- Chat messages are preserved when switching between different navigation tabs.
- The assistant's welcome message is only added once per session.
- New messages from both user and assistant are correctly appended to the global state and rendered.
