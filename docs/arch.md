## **Architecture Document: The AI Team Bot**

### 1. Executive Summary

The **AI Team Bot** is a multi-persona AI agent for Discord designed to assist software development teams. It leverages Retrieval-Augmented Generation (RAG) to provide contextually relevant answers from a project-specific knowledge base. The system features distinct AI "personas" (e.g., Project Manager, Lead Architect) that can be directly mentioned for targeted queries.

The bot's core innovation is its ability to proactively **interject** into conversations. Using a stateful conversation tracking system, it can understand the context of ongoing discussions and decide when a persona should contribute, even without being mentioned.

This architecture prioritizes phased implementation, high testability, and strategic use of sponsor technologies (Meta Llama, Cerebras, Docker) to deliver a powerful and polished hackathon project.

### 2. System Architecture Diagram

```mermaid
graph TD
    subgraph Discord
        User[Discord User]
    end

    subgraph "Docker Container"
        A[Bot Service / discord.py]
        B[Agent & Routing Logic]
        C[Configuration Manager]
        D[RAG & Vector Store]
        G[Conversational Context Manager]
    end

    subgraph "External Services"
        E[Discord API]
        F[Cerebras API for Meta Llama]
    end

    User -- "Sends Message" --> E
    E -- "Message Event" --> A
    A -- "Parses Message" --> B

    subgraph "Routing Decision"
        B -- "No Mention" --> G
        G -- "Routes to Conversation" --> B
        B -- "@Persona Mention" --> B
    end

    B -- "Gets Persona Config" --> C
    C -- "personas.json" --> B
    B -- "Selects Agent & Query" --> D
    D -- "Retrieves Context" --> B
    B -- "Crafts Prompt w/ Context" --> F
    F -- "LLM Inference" --> B
    B -- "Sends Response" --> A
    A -- "Uses Webhook for Persona" --> E
    E -- "Posts Message" --> User```

### 3. Core Components

#### 3.1. Discord Interface (`discord.py`)
*   **Responsibility:** Manages the connection to the Discord Gateway API, listens for `on_message` events, and sends responses.
*   **Persona Impersonation:** To give each persona a unique name and avatar, this component will manage **Discord Webhooks**.
    *   On first use in a channel, a webhook is created. The webhook URL is stored persistently (e.g., a `webhooks.json` file mapping `channel_id` to `webhook_url`) to avoid re-creation and rate-limiting.
    *   The bot requires the `MANAGE_WEBHOOKS` permission in the server.

#### 3.2. Agent & Routing Logic
*   **Responsibility:** The application's central controller. It inspects incoming messages and determines the appropriate action.
*   **Routing Scenarios:**
    1.  **Direct Mention (`@BotName`):** The message is routed to a default, general-purpose agent.
    2.  **Persona Mention (`@JohnPM`):** The message is routed to the specific agent for "JohnPM".
    3.  **No Mention (Interjection):** The message is passed to the **Conversational Context Manager** to be routed to an existing or new conversation, which then informs the interjection decision.

#### 3.3. Agent Core (`pydantic-ai`)
*   **Responsibility:** Defines the structure and behavior of individual AI agents.
*   **Implementation:** A central `AIAgent` class will be initialized with a `pydantic-ai` `Agent` instance (configured for the Cerebras model), a system prompt from the persona's configuration, and a RAG tool for knowledge retrieval.

#### 3.4. RAG System (Vector Store)
*   **Responsibility:** Ingests text documents, creates vector embeddings, and retrieves relevant text chunks based on a query.
*   **Implementation:** For hackathon speed, an in-memory vector store (e.g., FAISS) or a simple file-based database (e.g., ChromaDB) will be used. Each persona will have an isolated RAG index to ensure domain-specific knowledge retrieval.

#### 3.5. Conversational Context Management
*   **Responsibility:** Tracks ongoing discussions to enable stateful, context-aware routing for the Interjection feature. This is critical for handling low-information replies (e.g., "yes", "got it").
*   **State Store:** An in-memory dictionary mapping a `conversation_id` to an object containing:
    *   `last_updated`: Timestamp for temporal decay.
    *   `topic_embedding`: The vector embedding of an LLM-generated summary of the conversation.
    *   `recent_message_embeddings`: A fixed-size queue (e.g., 5) of the most recent message embeddings in the conversation.
*   **Routing Logic:** For every un-mentioned message, a hybrid score is calculated against all active conversations.
    *   **Formula:** `Relevance Score = (Topic Match * 0.4) + (Highest Message Match * 0.6)`
    *   **Topic Match:** Compares the new message embedding to the conversation's `topic_embedding` for broad context.
    *   **Message Match:** Compares the new message embedding to the `recent_message_embeddings` for immediate, tactical context. The high weight solves the "yes" problem by matching it to a preceding question.
    *   The message is routed to the conversation with the highest score above a set threshold; otherwise, a new conversation is created.

#### 3.6. Configuration Management
*   **Responsibility:** Externalizes all configuration.
*   **Implementation:** A `personas.json` file will define the AI team members.
    ```json
    [
      {
        "name": "JohnPM",
        "role": "Project Manager",
        "system_prompt": "You are John, the Project Manager...",
        "knowledge_base_path": "./kbs/project_management.txt"
      },
      {
        "name": "DaveArch",
        "role": "Lead Architect",
        "system_prompt": "You are Dave, the Lead Architect...",
        "knowledge_base_path": "./kbs/architecture_docs.md"
      }
    ]
    ```

#### 3.7. Deployment (`Dockerfile`)
*   **Responsibility:** Packages the application and its dependencies into a portable container.
*   **Structure:** Standard Python container setup including dependency installation, code copying, environment variable configuration (`DISCORD_TOKEN`, `CEREBRAS_API_KEY`), and setting the `CMD` to run the bot.

### 4. Data Models (Pydantic)

Structured, validated output is enforced through Pydantic models.

```python
from pydantic import BaseModel, Field
from typing import Optional

# For the Interjection Classifier agent
class InterjectionDecision(BaseModel):
    """A model to decide whether to interject in a conversation."""
    should_interject: bool = Field(description="Set to true if the conversation warrants an answer from an AI persona.")
    relevant_persona: Optional[str] = Field(description="The name of the most relevant persona to answer, e.g., 'JohnPM'.")
```

### 5. Phased Implementation & Test Plan

#### Phase 1: The Core RAG Engine
*   **Goal:** Create a standalone, command-line AI agent that returns a structured response from a knowledge base.
*   **Actions:** Implement the `AIAgent` class and a `RAGTool`. The agent should use `pydantic-ai` to return a validated `AgentResponse` model.
*   **Test Plan:** Use `pytest` and `pydantic-ai`'s `TestModel` to write unit tests that mock the LLM and verify the RAG tool is called correctly.

#### Phase 2: Discord `@Mention` Integration
*   **Goal:** Integrate the core agent into Discord, responding to direct mentions.
*   **Actions:** Create the basic `discord.py` bot. Implement an `on_message` listener that checks for mentions, instantiates the default `AIAgent`, and sends the response.
*   **Test Plan:** Manually test on a dedicated Discord server. `@BotName <question>` should return a RAG-based answer.

#### Phase 3: Multi-Persona Team & Dynamic RAG
*   **Goal:** Enable multiple, distinct personas, each with their own knowledge base and personality.
*   **Actions:** Implement the `ConfigurationManager` to load `personas.json`. Update `on_message` to detect persona mentions (`@JohnPM`), instantiate the correct agent, and use the webhook system to send the response with the persona's name and avatar.
*   **Test Plan:** Manually test that `@JohnPM` and `@DaveArch` respond with unique personalities, avatars, and draw from different knowledge bases.

#### Phase 4: Dockerization & Context-Aware Interjection
*   **Goal:** Containerize the application and implement the stateful, proactive interjection feature.
*   **Actions:**
    1.  Write the `Dockerfile` and confirm the application runs correctly as a container.
    2.  Implement the **Conversational Context Manager** component.
    3.  In the `on_message` handler for un-mentioned messages, use the manager's routing logic to attribute the message to a conversation.
    4.  Create a lightweight `ClassifierAgent` that takes the full conversation context (topic, recent messages) and returns an `InterjectionDecision`.
    5.  If `should_interject` is true, trigger the full RAG agent for the specified persona.
*   **Test Plan:**
    *   **Unit Tests:** Use `pytest` to test the conversation routing logic, ensuring low-information messages are correctly attributed.
    *   **Integration Tests:** In Discord, conduct a conversation. Verify that a relevant but un-mentioned question triggers an interjection from the correct persona.

#### Phase 5: Polish, Documentation, and Submission
*   **Goal:** Finalize the project for submission.
*   **Actions:** Add error handling, refactor code, and write a comprehensive `README.md` with clear `docker run` instructions.
*   **Test Plan:** Perform end-to-end testing of all features. Record a demo video showcasing both the persona-mention and proactive-interjection features.
