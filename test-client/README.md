# Document Chat Client

A Python chat application that connects to the lance-mcp server to provide conversational access to your documents using either Ollama or OpenAI models.

## Features

- 🔍 **Smart Document Search**: Automatically searches your document catalog and chunks for relevant information
- 🤖 **Multiple LLM Support**: Choose between Ollama (local) or OpenAI (cloud) models
- 💬 **Conversational Interface**: Natural chat with context awareness
- 🛠️ **Direct Tool Access**: Use MCP tools directly with commands
- 📚 **Rich Context**: Combines catalog and chunk search results for comprehensive answers

## Setup

### 1. Install Dependencies

```bash
cd client
pip install -r requirements.txt
```

### 2. Prepare the Lance MCP Server

Make sure you have:
- Built the lance-mcp server: `npm run build`
- Seeded your database: `npm run seed -- --dbpath my_doc_index --filesdir ./docs`

### 3. Setup LLM Providers

#### Ollama (Recommended for local use)
- Install Ollama: https://ollama.ai
- Pull a model: `ollama pull llama3.2`
- Make sure Ollama is running: `ollama serve`

#### OpenAI (Optional)
- Set your API key: `export OPENAI_API_KEY=your_api_key_here`

## Usage

### Basic Usage

```bash
python chat_app.py
```

### Custom Paths

```bash
python chat_app.py --server-path ../dist/index.js --db-path ../my_doc_index
```

## Commands

### Chat Commands
- Just type your question naturally
- The app will automatically search your documents and provide contextualized answers

### System Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/providers` | List available LLM providers |
| `/switch <name>` | Switch between providers (e.g., `/switch openai`) |
| `/tools` | Show available MCP tools |
| `/search <query>` | Search document catalog directly |
| `/chunks <query>` | Search document chunks directly |
| `/clear` | Clear conversation history |
| `/quit` | Exit the application |

## Example Session

```
💭 You: What documents do we have about healthcare?

🔍 Searching documents for relevant information...
🤖 Generating response with Ollama (llama3.2)...

🤖 Ollama (llama3.2):
Based on the document catalog, you have several healthcare-related documents:

1. **Chua_Kao-Ping_HealthCareSystemOverview_2006.pdf** - This primer provides an overview of the US healthcare system's structure and financing...

2. **Guide-to-U.S.-Healthcare-System.pdf** - This document explains how the country's pay-as-you-can-afford system works...

💭 You: Tell me about healthcare costs in the US

🔍 Searching documents for relevant information...
🤖 Generating response with Ollama (llama3.2):
[Detailed response about healthcare costs based on document content]

💭 You: /switch openai
🔄 Switched to: OpenAI (gpt-4o-mini)

💭 You: /quit
👋 Goodbye!
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chat App      │◄──►│   MCP Client     │◄──►│  Lance MCP      │
│                 │    │                  │    │   Server        │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • UI/Commands   │    │ • JSON-RPC       │    │ • Tool Registry │
│ • Conversation  │    │ • Tool Calls     │    │ • LanceDB      │
│ • LLM Manager   │    │ • Async I/O      │    │ • Vector Search │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                            ┌─────────────────┐
│  LLM Providers  │                            │   Document      │
│                 │                            │   Database      │
├─────────────────┤                            ├─────────────────┤
│ • Ollama        │                            │ • Catalog Table │
│ • OpenAI        │                            │ • Chunks Table  │
└─────────────────┘                            └─────────────────┘
```

## Troubleshooting

### Connection Issues
- **MCP Server**: Ensure the server path is correct and you've run `npm run build`
- **Database**: Make sure the database path exists and you've run the seed command
- **Ollama**: Check that Ollama is running on `http://127.0.0.1:11434`

### No Documents Found
- Verify your database was seeded properly
- Check that your documents are in supported formats (PDF)
- Use `/tools` command to verify MCP tools are available

### LLM Errors
- **Ollama**: Ensure the model is pulled (`ollama pull llama3.2`)
- **OpenAI**: Verify your API key is set correctly

## Customization

### Adding New LLM Providers
Extend the `LLMProvider` class in `llm_provider.py`:

```python
class MyCustomProvider(LLMProvider):
    async def chat(self, messages: List[ChatMessage], tools_context: Optional[str] = None) -> str:
        # Your implementation
        pass
```

### Modifying Search Behavior
Edit the `_get_relevant_context` method in `chat_app.py` to customize how document context is retrieved.