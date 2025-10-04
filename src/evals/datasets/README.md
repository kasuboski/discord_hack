# Evaluation Datasets

This directory contains test datasets for evaluating the Discord AI Team Bot's router and persona agents. All datasets are in YAML format and are version-controlled for reviewability and tracking.

## Overview

Each dataset focuses on testing specific aspects of the bot's behavior:

- **`router_persona_selection.yaml`**: Tests whether the router correctly suggests the appropriate persona based on message content
- **`router_structured_output.yaml`**: Tests whether the router always returns valid, well-formed `RouterDecision` objects
- **`router_context_selection.yaml`** (future): Tests context message selection from conversation history
- **`router_conversation_routing.yaml`** (future): Tests conversation thread identification and routing

## Dataset Structure

All datasets follow the pydantic-evals format:

```yaml
cases:
  - name: descriptive_test_case_name
    inputs:
      # Input data structure (varies by dataset)
    expected_output:
      # Expected output (or null for structure-only tests)
    metadata:
      # Additional metadata for categorization and filtering
    evaluators:
      # List of evaluator classes to run on this case
```

## Current Datasets

### router_persona_selection.yaml

**Purpose**: Validates that the router suggests the correct persona based on message content.

**Test Coverage** (15 cases):
- **Project Management (JohnPM)**: 4 cases
  - Timeline/deadline questions
  - Sprint planning and scheduling
  - Requirements and acceptance criteria
  - Stakeholder communication
- **Architecture (SarahArch)**: 4 cases
  - System design patterns (microservices vs monolith)
  - Authentication/security architecture
  - Database technology selection
  - Caching and infrastructure design
- **Development (DevMike)**: 4 cases
  - Debugging (async/await, test failures)
  - Code review requests
  - Implementation guidance
- **Ambiguous Cases**: 3 cases
  - Mixed PM/Dev topics (timeline + implementation)
  - Mixed Arch/PM topics (scalability + business)
  - Very vague questions (minimal context)

**Key Fields**:
- `expected_output.suggested_persona`: Expected persona name ("JohnPM", "SarahArch", or "DevMike")
- `expected_output.confidence`: Minimum acceptable confidence (0.8+ for clear, 0.6+ for ambiguous)
- `metadata.category`: Category ("project_management", "architecture", "development", "ambiguous")
- `metadata.difficulty`: "easy", "medium", or "hard"
- `metadata.acceptable_personas`: List of personas (for ambiguous cases where multiple are acceptable)

### router_structured_output.yaml

**Purpose**: Ensures the router always returns valid, well-formed structured output regardless of input.

**Test Coverage** (10 cases):
- **Valid Output Cases**: 3 cases
  - Simple case with no context
  - Case with conversation context
  - Case with no relevant context (empty message IDs)
- **Edge Cases**: 5 cases
  - Empty conversations list
  - Very short message ("?")
  - Very long message (multi-topic)
  - Message with attachments
  - Explicit persona mention
- **Confidence Bounds**: 2 cases
  - Clear case (should have high confidence)
  - Ambiguous case (should have lower confidence)

**Key Validations** (via `StructuredOutputEvaluator`):
- Output is a valid `RouterDecision` Pydantic model
- `confidence` is between 0.0 and 1.0
- `reasoning` field is non-empty
- All `relevant_message_ids` exist in provided conversations
- `suggested_persona` is one of `available_personas` or null
- `conversation_id` matches an active conversation or is null
- `should_respond` is True when `is_bot_mentioned` is True

## ConversationMessage Field Reference

All test cases use the `ConversationMessage` data structure with these fields:

### Core Message Data
- **`id`** (str): Unique message ID (e.g., "msg_1001")
- **`content`** (str): The message text
- **`author_name`** (str): Display name of message author
- **`author_id`** (str): Unique ID of message author
- **`timestamp`** (str): ISO 8601 timestamp (e.g., "2025-10-01T10:00:00Z")
- **`channel_id`** (str): Discord channel ID where message was sent

### Bot-Specific Metadata
- **`is_bot`** (bool): True if message was sent by a bot
- **`persona_name`** (str | null): If bot message, which persona sent it (e.g., "JohnPM", "SarahArch", "DevMike")

### Conversation Threading Metadata
- **`reply_to_id`** (str | null): If replying to another message, the ID of that message
- **`mentions_user_ids`** (list[str]): User IDs mentioned in the message (for @mentions)

### Rich Content Indicators
- **`has_attachments`** (bool): True if message has files/images attached
- **`attachment_types`** (list[str]): MIME types of attachments (e.g., ["image/png", "application/pdf"])
- **`has_embeds`** (bool): True if message has rich embeds

### Example Message

```yaml
current_message:
  id: "msg_1001"
  content: "What's the deadline for the Q1 release?"
  author_name: "TestUser"
  author_id: "user_123"
  timestamp: "2025-10-01T10:00:00Z"
  channel_id: "channel_1"
  is_bot: false
  persona_name: null
  reply_to_id: null
  mentions_user_ids: []
  has_attachments: false
  attachment_types: []
  has_embeds: false
```

## Available Personas

All test cases use these three personas:

1. **JohnPM** (John Parker)
   - Role: Project Manager
   - Expertise: Timelines, planning, requirements, stakeholder communication

2. **SarahArch** (Sarah Chen)
   - Role: Lead Architect
   - Expertise: System design, architecture patterns, technology choices, scalability

3. **DevMike** (Mike Rodriguez)
   - Role: Senior Developer
   - Expertise: Implementation, debugging, code review, testing

## Adding New Test Cases

To add a new test case to an existing dataset:

1. **Choose descriptive name**: Use format `{category}_{specific_scenario}` (e.g., `pm_risk_assessment`, `arch_api_design`)

2. **Fill in all message fields**: Use the `ConversationMessage` structure above. Don't skip fields - set them to appropriate defaults (null, [], false, etc.)

3. **Use realistic content**: Write actual questions/messages that users would send in Discord

4. **Set appropriate timestamps**: Use ISO 8601 format. Make timestamps logical (replies come after original messages)

5. **Define expected output**: For persona selection, specify the expected persona and minimum confidence. For structure validation, set to `null`.

6. **Add metadata**: Include category, subcategory, difficulty, and any notes

7. **Specify evaluators**: List which evaluator classes should run on this case

### Example Template

```yaml
- name: descriptive_test_case_name
  inputs:
    current_message:
      id: "msg_XXXX"
      content: "Your realistic question here"
      author_name: "TestUser"
      author_id: "user_123"
      timestamp: "2025-10-01T10:00:00Z"
      channel_id: "channel_1"
      is_bot: false
      persona_name: null
      reply_to_id: null
      mentions_user_ids: []
      has_attachments: false
      attachment_types: []
      has_embeds: false
    active_conversations: []  # or list of ConversationThread objects
    available_personas:
      - name: "JohnPM"
        role: "Project Manager"
      - name: "SarahArch"
        role: "Lead Architect"
      - name: "DevMike"
        role: "Senior Developer"
    explicit_persona: null
    is_bot_mentioned: true
  expected_output:
    should_respond: true
    conversation_id: null
    suggested_persona: "PersonaName"
    relevant_message_ids: []
    confidence: 0.8
    reasoning: "Expected reasoning"
    topic_summary: "Brief topic summary"
  metadata:
    category: "category_name"
    subcategory: "subcategory_name"
    difficulty: "easy"
    expected_persona: "PersonaName"
  evaluators:
    - PersonaSuggestionEvaluator
    - StructuredOutputEvaluator
```

## Running Evaluations

See `/Users/josh/projects/discord_hack/EVALS.md` for full documentation on running evals.

Quick start:
```bash
# Run all datasets
uv run src/evals/run_evals.py

# Run specific dataset
uv run src/evals/run_evals.py --dataset router_persona_selection

# Run with different model
uv run src/evals/run_evals.py --model llama3.1-70b
```

## Future Datasets

The following datasets are planned but not yet implemented (they require the conversation/context system to be fully operational):

- **`router_context_selection.yaml`**: Test which messages the router selects as relevant context
- **`router_conversation_routing.yaml`**: Test conversation thread identification and routing
- **`router_should_respond.yaml`**: Test proactive response decisions
- **`persona_response_format.yaml`**: Test persona agent response quality and format

## References

- **Full Evaluation Design**: `/Users/josh/projects/discord_hack/EVALS.md`
- **Router Implementation**: `/Users/josh/projects/discord_hack/src/discord_hack/router.py`
- **Conversation Store**: `/Users/josh/projects/discord_hack/src/discord_hack/conversation_store.py`
- **Persona Configs**: `/Users/josh/projects/discord_hack/personas.json`
