# Persona Configuration System

The AI Team Bot's persona system allows you to create and manage multiple AI assistants, each with their own personality, expertise, knowledge base, and visual appearance. This document covers everything you need to know about configuring, using, and extending personas.

## Table of Contents

- [Overview](#overview)
- [Configuration File Structure](#configuration-file-structure)
- [Persona Properties](#persona-properties)
- [Knowledge Bases](#knowledge-bases)
- [Avatar System](#avatar-system)
- [Using Personas](#using-personas)
- [Creating New Personas](#creating-new-personas)
- [Modifying Existing Personas](#modifying-existing-personas)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Technical Implementation](#technical-implementation)

## Overview

The persona system is built around a JSON configuration file (`personas.json`) that defines each AI team member. Each persona has:

- **Unique Identity**: Name, display name, and role
- **Visual Appearance**: Custom avatar generated via DiceBear API
- **Personality**: System prompt that defines behavior and expertise
- **Knowledge Base**: Domain-specific text files for RAG (Retrieval-Augmented Generation)
- **Discord Integration**: Webhook-based impersonation with custom names and avatars

## Configuration File Structure

The main configuration is stored in `personas.json` at the project root:

```json
[
  {
    "name": "JohnPM",
    "display_name": "John Parker",
    "role": "Project Manager",
    "avatar_url": "https://api.dicebear.com/7.x/personas/svg?seed=JohnPM&backgroundColor=b6e3f4&clothingColor=0ea5e9",
    "system_prompt": "You are John Parker, an experienced Project Manager...",
    "knowledge_base_path": "./kbs/project_management.txt"
  },
  {
    "name": "SarahArch",
    "display_name": "Sarah Chen", 
    "role": "Lead Architect",
    "avatar_url": "https://api.dicebear.com/7.x/personas/svg?seed=SarahArch&backgroundColor=fecaca&clothingColor=dc2626",
    "system_prompt": "You are Sarah Chen, a Lead Software Architect...",
    "knowledge_base_path": "./kbs/architecture.txt"
  }
]
```

The configuration is an array of persona objects, where each object represents a single AI team member.

## Persona Properties

Each persona must include the following properties:

### Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | The mention handle for Discord (e.g., "JohnPM" for `@JohnPM`) |
| `display_name` | string | The human-readable full name shown in Discord |
| `role` | string | The persona's job title or area of expertise |
| `avatar_url` | string | URL to the persona's avatar image |
| `system_prompt` | string | The AI system prompt defining personality and behavior |
| `knowledge_base_path` | string | Relative or absolute path to the knowledge base file |

### Property Guidelines

- **name**: Should be short, memorable, and unique. Used for Discord mentions (`@PersonaName`)
- **display_name**: Full professional name as it would appear in a real team
- **role**: Clear, descriptive job title that indicates the persona's expertise area
- **avatar_url**: Must be a publicly accessible image URL (DiceBear recommended)
- **system_prompt**: Should be detailed, defining personality, expertise, communication style
- **knowledge_base_path**: Path relative to project root (e.g., `./kbs/filename.txt`)

## Knowledge Bases

Knowledge bases are text files containing domain-specific information that personas use to answer questions. They're stored in the `kbs/` directory.

### Knowledge Base Structure

Knowledge bases should be well-structured text files with:

- **Clear headings and sections** using markdown-style formatting
- **Comprehensive coverage** of the persona's domain
- **Practical, actionable information** rather than just theory
- **Examples and specific guidance** where applicable
- **Best practices and common patterns** in the field

### Example Knowledge Base Structure

```
# Project Management Knowledge Base - John Parker

## Project Management Fundamentals
### Agile Methodologies
- Scrum: 2-4 week sprints with daily standups...
- Kanban: Continuous flow with WIP limits...

### Project Planning Best Practices
- Break down large features into smaller tasks...
- Use story points for relative estimation...

## Risk Management
### Technical Risks
- Unproven technologies, complex integrations...
### Mitigation Strategies
- Proof of concepts, cross-training, buffer time...

## Tool Recommendations
- Project Tracking: Jira, Azure DevOps, Linear...
```

### Creating Knowledge Bases

1. **Research the Domain**: Gather comprehensive information about the expertise area
2. **Organize Hierarchically**: Use clear headings and subheadings
3. **Include Examples**: Provide concrete examples and scenarios
4. **Keep Current**: Update with modern practices and tools
5. **Size Appropriately**: Aim for comprehensive coverage without overwhelming the RAG system

## Avatar System

Personas use the DiceBear API to generate consistent, professional avatars. The avatar URL format is:

```
https://api.dicebear.com/7.x/personas/svg?seed=PERSONA_NAME&backgroundColor=COLOR1&clothingColor=COLOR2
```

### Avatar Parameters

- `seed`: Unique identifier (typically the persona name)
- `backgroundColor`: Hex color for background (without #)
- `clothingColor`: Hex color for clothing (without #)

### Color Schemes

Use distinct color schemes for easy visual identification:

- **Blue Theme**: `backgroundColor=b6e3f4&clothingColor=0ea5e9`
- **Red Theme**: `backgroundColor=fecaca&clothingColor=dc2626` 
- **Green Theme**: `backgroundColor=d1fae5&clothingColor=059669`
- **Purple Theme**: `backgroundColor=e9d5ff&clothingColor=7c3aed`
- **Orange Theme**: `backgroundColor=fed7aa&clothingColor=ea580c`

## Using Personas

### Discord Interaction

#### Direct Mention
Mention a persona directly to get a targeted response from their expertise domain:

```
@JohnPM How should we prioritize these new feature requests?
@SarahArch What's the best architecture pattern for this microservices setup?
@DevMike Can you help me debug this API integration issue?
```

#### General Bot Mention
Mention the bot generally for non-specific queries:

```
@AITeamBot What can you help me with?
@AITeamBot Tell me about the team
```

### Response Behavior

- **Persona-Specific**: Each persona responds with their unique personality and knowledge
- **Visual Identity**: Responses appear with the persona's name and avatar
- **Domain Expertise**: Answers are informed by the persona's knowledge base
- **Consistent Character**: Each persona maintains their defined personality across interactions

## Creating New Personas

### Step 1: Define the Persona

Determine:
- **Expertise Area**: What domain will they cover?
- **Personality**: What's their communication style?
- **Name**: What will their mention handle be?
- **Background**: What's their professional experience?

### Step 2: Create the Knowledge Base

1. Create a new file in `kbs/`: `kbs/new_domain.txt`
2. Structure the content with clear sections and headings
3. Include comprehensive information about the domain
4. Add practical examples and best practices

### Step 3: Generate Avatar

1. Choose a unique seed name
2. Select a color scheme not used by other personas
3. Generate the DiceBear URL
4. Test the URL to ensure it renders correctly

### Step 4: Write System Prompt

Create a detailed system prompt that includes:
- **Identity**: Name, role, years of experience
- **Expertise**: Specific areas of knowledge
- **Personality**: Communication style, preferences
- **Behavior**: How they should respond to queries

Example system prompt structure:

```
You are [Name], a [Role] with [X] years of experience in [Domain]. 
You focus on [Specific Areas]. You're [Personality Traits], and [Communication Style].
Keep responses [Style Guidelines], often [Behavioral Patterns].
```

### Step 5: Add to Configuration

Add the new persona object to `personas.json`:

```json
{
  "name": "NewPersona",
  "display_name": "Full Name", 
  "role": "Professional Role",
  "avatar_url": "https://api.dicebear.com/7.x/personas/svg?seed=NewPersona&backgroundColor=COLOR1&clothingColor=COLOR2",
  "system_prompt": "Detailed system prompt defining the persona...",
  "knowledge_base_path": "./kbs/new_domain.txt"
}
```

### Step 6: Test the Persona

1. Restart the bot to load the new configuration
2. Test basic interaction: `@NewPersona hello`
3. Test domain expertise with specific questions
4. Verify the avatar and name appear correctly
5. Check that responses align with the intended personality

## Modifying Existing Personas

### Updating Configuration

1. **Edit `personas.json`**: Modify the desired persona's properties
2. **Restart Bot**: The bot must be restarted to load configuration changes
3. **Test Changes**: Verify the modifications work as expected

### Updating Knowledge Bases

Knowledge base updates take effect immediately:

1. **Edit the knowledge base file** in the `kbs/` directory
2. **No restart required**: Changes are loaded dynamically
3. **Test with queries**: Ask questions that would use the new information

### Updating System Prompts

1. **Modify the `system_prompt`** field in `personas.json`
2. **Restart the bot** to load the new prompt
3. **Test personality changes**: Verify the persona behaves differently

## Best Practices

### Persona Design

- **Distinct Expertise**: Each persona should have a clear, non-overlapping domain
- **Unique Personalities**: Give each persona a distinct communication style
- **Professional Credibility**: Ground personas in realistic experience and expertise
- **Consistent Character**: Maintain the persona's identity across all interactions

### Knowledge Base Management

- **Regular Updates**: Keep knowledge bases current with industry best practices
- **Quality Content**: Focus on practical, actionable information
- **Appropriate Scope**: Don't make knowledge bases too broad or too narrow
- **Clear Organization**: Use consistent formatting and hierarchical structure

### Configuration Management

- **Version Control**: Keep `personas.json` in version control
- **Backup Knowledge Bases**: Maintain backups of all knowledge base files
- **Testing Protocol**: Always test personas after configuration changes
- **Documentation**: Document any custom personas or modifications

### Avatar Management

- **Consistent Style**: Use the same avatar generator for all personas
- **Color Coding**: Assign distinct colors to make personas easily recognizable
- **Professional Appearance**: Ensure avatars look appropriate for a work environment
- **URL Stability**: Use reliable, permanent URLs for avatars

## Troubleshooting

### Common Issues

#### Persona Not Responding

**Symptoms**: No response when mentioning a persona
**Solutions**:
- Check that the persona name in `personas.json` matches the Discord mention
- Verify the `CEREBRAS_API_KEY` environment variable is set
- Check bot logs for error messages
- Ensure the bot has restarted since configuration changes

#### Knowledge Base Errors

**Symptoms**: "Knowledge base not found" or empty responses
**Solutions**:
- Verify the `knowledge_base_path` exists and is readable
- Check file permissions on the knowledge base file
- Ensure the path is relative to the project root
- Look for typos in the file path

#### Avatar Not Displaying

**Symptoms**: Default Discord avatar instead of persona avatar
**Solutions**:
- Test the `avatar_url` in a web browser
- Check for typos in the DiceBear URL
- Verify the bot has `MANAGE_WEBHOOKS` permission
- Check Discord webhook limits haven't been exceeded

#### Webhook Permission Issues

**Symptoms**: "Missing permissions to create webhook" errors
**Solutions**:
- Ensure the bot has `MANAGE_WEBHOOKS` permission in the server
- Check channel-specific permission overrides
- Verify the bot role has sufficient permissions
- Try using the persona in a different channel

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOGLEVEL=DEBUG
uv run src/main.py discord
```

This will show detailed logs about:
- Configuration loading
- Persona agent creation
- Webhook management
- RAG processing
- Error details

## Technical Implementation

### Configuration Loading

The `ConfigManager` class handles:
- Loading `personas.json` at startup
- Validating persona configurations using Pydantic models
- Resolving knowledge base file paths
- Providing lookup methods for persona discovery
- Supporting configuration reloading without restart

### Webhook Management

The `WebhookManager` class provides:
- Automatic webhook creation per Discord channel
- Persistent caching in `webhooks.json` to avoid rate limits
- Graceful fallback to regular messages when webhooks fail
- Clean error handling for permission issues

### Agent Creation

Each persona gets:
- A unique `pydantic-ai` agent instance
- Custom system prompt defining personality and expertise
- Access to their specific knowledge base via RAG tools
- Consistent behavior across multiple interactions

### Message Processing

The bot processes messages in this order:
1. **Persona Mention Detection**: Check for `@PersonaName` patterns
2. **Configuration Lookup**: Find the persona's configuration
3. **Agent Processing**: Run the query through the persona's RAG agent
4. **Response Delivery**: Send via webhook as the persona or fallback to regular message

### Performance Optimizations

- **Agent Caching**: Persona agents are created once and reused
- **Webhook Caching**: Webhook URLs are persisted to avoid recreation
- **Lazy Loading**: Configuration is loaded on first access
- **Efficient Pattern Matching**: Regex-based mention detection

This technical foundation supports the robust, scalable persona system that makes the AI Team Bot unique and powerful.