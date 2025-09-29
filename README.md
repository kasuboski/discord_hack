# AI Team Bot
The **AI Team Bot** is a multi-persona AI agent for Discord designed to assist software development teams. It leverages Retrieval-Augmented Generation (RAG) to provide contextually relevant answers from a project-specific knowledge base. The system features distinct AI "personas" (e.g., Project Manager, Lead Architect) that can be directly mentioned for targeted queries.

The bot's core innovation is its ability to proactively **interject** into conversations. Using a stateful conversation tracking system, it can understand the context of ongoing discussions and decide when a persona should contribute, even without being mentioned.

## Tech Stack
* Python
* UV
* Pydantic AI
* Discord Py
