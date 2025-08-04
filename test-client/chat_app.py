#!/usr/bin/env python3
"""
Interactive Chat App for Lance MCP
Supports both Ollama and OpenAI providers
"""
import asyncio
import os
import sys
from typing import List, Optional
import argparse
from pathlib import Path

from mcp_client import MCPClient
from llm_provider import LLMManager, ChatMessage


class DocumentChatApp:
    def __init__(self, server_path: str, db_path: str):
        self.mcp_client = MCPClient(server_path, db_path)
        self.llm_manager = LLMManager()
        self.conversation: List[ChatMessage] = []
        self.running = True
        
    async def setup(self):
        """Initialize the app"""
        print("🚀 Starting Document Chat App...")
        
        # Connect to MCP server
        print("📡 Connecting to lance-mcp server...")
        try:
            await self.mcp_client.connect()
            tools = self.mcp_client.get_available_tools()
            print(f"✅ Connected! Available tools: {[t.name for t in tools]}")
        except Exception as e:
            print(f"❌ Failed to connect to MCP server: {e}")
            print("Make sure the server path and database path are correct.")
            return False
            
        # Setup LLM providers
        await self._setup_llm_providers()
        
        return True
    
    async def _setup_llm_providers(self):
        """Setup available LLM providers"""
        print("\n🤖 Setting up LLM providers...")
        
        # Add Ollama provider (always available)
        try:
            self.llm_manager.add_ollama_provider("ollama", "llama3.2")
            print("✅ Ollama provider added (llama3.2)")
        except Exception as e:
            print(f"⚠️  Ollama provider setup failed: {e}")
        
        # Add OpenAI provider if API key is available
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                self.llm_manager.add_openai_provider("openai", openai_key)
                print("✅ OpenAI provider added (gpt-4o-mini)")
            except Exception as e:
                print(f"⚠️  OpenAI provider setup failed: {e}")
        else:
            print("💡 Set OPENAI_API_KEY environment variable to use OpenAI")
        
        providers = self.llm_manager.list_providers()
        if providers:
            current = self.llm_manager.current_provider
            print(f"🎯 Current provider: {current}")
            print(f"📋 Available providers: {', '.join(providers)}")
        else:
            print("❌ No LLM providers available!")
            return False
        
        return True
    
    def _print_help(self):
        """Print help message"""
        print("""
📚 Document Chat Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Chat Commands:
   Just type your question to chat with the documents
   
🔧 System Commands:
   /help          - Show this help
   /providers     - List available LLM providers  
   /switch <name> - Switch to a different provider
   /tools         - Show available MCP tools
   /search <query> - Search document catalog
   /chunks <query> - Search document chunks
   /clear         - Clear conversation history
   /quit          - Exit the app

💡 Examples:
   What documents do we have?
   /search healthcare system
   Tell me about the US healthcare costs
   /switch openai
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
    
    async def _handle_command(self, user_input: str) -> bool:
        """Handle system commands. Returns True if command was handled."""
        if not user_input.startswith('/'):
            return False
            
        parts = user_input[1:].split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "help":
            self._print_help()
        elif command == "quit" or command == "exit":
            print("👋 Goodbye!")
            self.running = False
        elif command == "clear":
            self.conversation.clear()
            print("🧹 Conversation cleared!")
        elif command == "providers":
            providers = self.llm_manager.list_providers()
            current = self.llm_manager.current_provider
            print(f"🎯 Current: {current}")
            for p in providers:
                provider = self.llm_manager.providers[p]
                status = "✅" if p == current else "  "
                print(f"{status} {p}: {provider.get_name()}")
        elif command == "switch":
            if not args:
                print("❌ Please specify provider name. Use /providers to see available options.")
            else:
                try:
                    self.llm_manager.set_current_provider(args)
                    provider = self.llm_manager.get_current_provider()
                    print(f"🔄 Switched to: {provider.get_name()}")
                except ValueError as e:
                    print(f"❌ {e}")
        elif command == "tools":
            tools = self.mcp_client.get_available_tools()
            print("🛠️  Available MCP Tools:")
            for tool in tools:
                print(f"   • {tool.name}: {tool.description}")
        elif command == "search":
            if not args:
                print("❌ Please provide a search query")
            else:
                print(f"🔍 Searching catalog for: {args}")
                try:
                    result = await self.mcp_client.search_catalog(args)
                    print(f"📄 Result:\n{result}")
                except Exception as e:
                    print(f"❌ Search error: {e}")
        elif command == "chunks":
            if not args:
                print("❌ Please provide a search query")
            else:
                print(f"🔍 Searching chunks for: {args}")
                try:
                    result = await self.mcp_client.search_chunks(args)
                    print(f"📄 Result:\n{result}")
                except Exception as e:
                    print(f"❌ Search error: {e}")
        else:
            print(f"❌ Unknown command: {command}. Type /help for available commands.")
        
        return True
    
    async def _get_relevant_context(self, query: str) -> str:
        """Get relevant context from documents for the query"""
        context_parts = []
        
        try:
            # Search catalog first
            catalog_result = await self.mcp_client.search_catalog(query)
            if catalog_result and "Error:" not in catalog_result:
                context_parts.append(f"📋 Document Catalog Results:\n{catalog_result}")
            
            # Search chunks for detailed information
            chunks_result = await self.mcp_client.search_chunks(query)
            if chunks_result and "Error:" not in chunks_result:
                context_parts.append(f"📄 Document Chunks:\n{chunks_result}")
                
        except Exception as e:
            context_parts.append(f"⚠️ Error retrieving context: {e}")
        
        return "\n\n".join(context_parts) if context_parts else None
    
    async def _handle_chat(self, user_input: str):
        """Handle chat messages"""
        print("🔍 Searching documents for relevant information...")
        
        # Get relevant context from documents
        context = await self._get_relevant_context(user_input)
        
        # Add user message to conversation
        user_message = ChatMessage(role="user", content=user_input)
        self.conversation.append(user_message)
        
        # Get LLM response
        provider = self.llm_manager.get_current_provider()
        if not provider:
            print("❌ No LLM provider available!")
            return
        
        print(f"🤖 Generating response with {provider.get_name()}...")
        
        try:
            response = await provider.chat(self.conversation, tools_context=context)
            
            # Add assistant response to conversation
            assistant_message = ChatMessage(role="assistant", content=response)
            self.conversation.append(assistant_message)
            
            print(f"\n🤖 {provider.get_name()}:")
            print(response)
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
    
    async def run(self):
        """Main chat loop"""
        if not await self.setup():
            return
        
        print("\n" + "="*60)
        print("🎉 Welcome to Document Chat!")
        print("Type your questions or use /help for commands")
        print("="*60)
        
        while self.running:
            try:
                user_input = input("\n💭 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle system commands
                if await self._handle_command(user_input):
                    continue
                
                # Handle chat
                await self._handle_chat(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
        
        # Cleanup
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up...")
        await self.mcp_client.close()
        await self.llm_manager.close_all()


async def main():
    parser = argparse.ArgumentParser(description="Document Chat App using Lance MCP")
    parser.add_argument(
        "--server-path", 
        default="../dist/index.js",
        help="Path to the lance-mcp server script"
    )
    parser.add_argument(
        "--db-path",
        default="../my_doc_index", 
        help="Path to the LanceDB database"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    server_path = Path(args.server_path).resolve()
    if not server_path.exists():
        print(f"❌ Server path not found: {server_path}")
        print("Make sure you've built the lance-mcp server with 'npm run build'")
        sys.exit(1)
    
    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        print(f"❌ Database path not found: {db_path}")
        print("Make sure you've seeded the database with 'npm run seed'")
        sys.exit(1)
    
    app = DocumentChatApp(str(server_path), str(db_path))
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())