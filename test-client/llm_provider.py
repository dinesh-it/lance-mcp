"""
LLM Provider abstraction supporting both Ollama and OpenAI
"""
import asyncio
import aiohttp
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system"
    content: str


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[ChatMessage], tools_context: Optional[str] = None) -> str:
        """Generate a chat response"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name"""
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.2", base_url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url
        self.session = None
    
    async def _ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def chat(self, messages: List[ChatMessage], tools_context: Optional[str] = None) -> str:
        await self._ensure_session()
        
        # Convert messages to Ollama format
        ollama_messages = []
        
        # Add system message with tools context if provided
        if tools_context:
            system_prompt = f"""You are a helpful assistant that can search and analyze documents. 
You have access to document search tools that have provided this relevant information:

{tools_context}

Use this information to answer the user's question. Be specific and cite the information from the documents when relevant."""
            ollama_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation messages
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("message", {}).get("content", "No response")
                else:
                    return f"Error: HTTP {response.status}"
        except Exception as e:
            return f"Error connecting to Ollama: {e}"
    
    def get_name(self) -> str:
        return f"Ollama ({self.model})"
    
    async def close(self):
        if self.session:
            await self.session.close()


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.session = None
    
    async def _ensure_session(self):
        if not self.session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def chat(self, messages: List[ChatMessage], tools_context: Optional[str] = None) -> str:
        await self._ensure_session()
        
        # Convert messages to OpenAI format
        openai_messages = []
        
        # Add system message with tools context if provided
        if tools_context:
            system_prompt = f"""You are a helpful assistant that can search and analyze documents. 
You have access to document search tools that have provided this relevant information:

{tools_context}

Use this information to answer the user's question. Be specific and cite the information from the documents when relevant."""
            openai_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation messages
        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})
        
        payload = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"Error: HTTP {response.status} - {error_text}"
        except Exception as e:
            return f"Error connecting to OpenAI: {e}"
    
    def get_name(self) -> str:
        return f"OpenAI ({self.model})"
    
    async def close(self):
        if self.session:
            await self.session.close()


class LLMManager:
    """Manages multiple LLM providers"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.current_provider: Optional[str] = None
    
    def add_ollama_provider(self, name: str, model: str = "llama3.2", base_url: str = "http://127.0.0.1:11434"):
        """Add an Ollama provider"""
        self.providers[name] = OllamaProvider(model, base_url)
        if not self.current_provider:
            self.current_provider = name
    
    def add_openai_provider(self, name: str, api_key: str, model: str = "gpt-4o-mini"):
        """Add an OpenAI provider"""
        self.providers[name] = OpenAIProvider(api_key, model)
        if not self.current_provider:
            self.current_provider = name
    
    def set_current_provider(self, name: str):
        """Set the current active provider"""
        if name in self.providers:
            self.current_provider = name
        else:
            raise ValueError(f"Provider '{name}' not found")
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """Get the current active provider"""
        if self.current_provider:
            return self.providers[self.current_provider]
        return None
    
    def list_providers(self) -> List[str]:
        """List all available providers"""
        return list(self.providers.keys())
    
    async def close_all(self):
        """Close all provider sessions"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()