"""
LLM Providers - Multi-provider abstraction for DataCursor.
Supports OpenAI, Anthropic, Google, and Ollama (local).
"""

import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum

from data_scientist_prompt import DATA_SCIENTIST_SYSTEM_PROMPT, DATA_SCIENTIST_CODE_PROMPT


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENROUTER = "openrouter"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise ValueError("OpenAI API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise ValueError("Anthropic API key not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "system": system_prompt or DATA_SCIENTIST_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model = model
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise ValueError("Google API key not configured")
        
        # Use langchain for Google
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self.api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
        )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = llm.invoke(messages)
        return response.content


class GroqProvider(LLMProvider):
    """Groq provider using Llama 3."""
    
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise ValueError("Groq API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                },
                timeout=60.0,
            )
            if response.status_code != 200:
                print(f"Groq API Error: {response.text}") 
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, model: str = "codellama", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def is_configured(self) -> bool:
        # Check if Ollama is running
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        # Check if model exists, otherwise try to find fallback
        available_models = await self.list_models()
        model_to_use = self.model
        
        if available_models and self.model not in available_models:
            # Fallback to first available model
            print(f"Model {self.model} not found. Falling back to {available_models[0]}")
            model_to_use = available_models[0]
        elif not available_models:
            raise ValueError("No Ollama models found. Please run 'ollama pull codellama' or similar.")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_to_use,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=120.0,  # Local models can be slower
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
    
    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            return []


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider."""
    
    def __init__(self, api_key: str = None, model: str = "google/gemini-2.0-flash-exp:free"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, system_prompt: str = None) -> str:
        if not self.is_configured():
            raise ValueError("OpenRouter API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://datacursor.com",
                    "X-Title": "DataCursor",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class LLMManager:
    """
    Manages LLM providers and handles code generation.
    """
    
    def __init__(self):
        self.providers: dict[ProviderType, LLMProvider] = {}
        self.active_provider: ProviderType = ProviderType.GOOGLE
        self.use_data_scientist_persona: bool = True
        
        # Initialize with environment variables
        self._init_providers()
    
    def _init_providers(self):
        """Initialize providers from environment."""
        self.providers[ProviderType.OPENAI] = OpenAIProvider()
        self.providers[ProviderType.ANTHROPIC] = AnthropicProvider()
        self.providers[ProviderType.GOOGLE] = GoogleProvider()
        self.providers[ProviderType.OLLAMA] = OllamaProvider()
        
        # Configure Groq with user-provided key if not in env
        groq_key = os.environ.get("GROQ_API_KEY")
        self.providers[ProviderType.GROQ] = GroqProvider(api_key=groq_key)

        # Configure OpenRouter with user-provided key if not in env
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        self.providers[ProviderType.OPENROUTER] = OpenRouterProvider(api_key=openrouter_key)
        
        # Set Groq as default if configured
        # Set OpenRouter as default if configured, otherwise Groq
        # Set Groq as default (Prioritize over OpenRouter due to rate limits)
        if self.providers[ProviderType.GROQ].is_configured():
            self.active_provider = ProviderType.GROQ
        elif self.providers[ProviderType.OPENROUTER].is_configured():
            self.active_provider = ProviderType.OPENROUTER
    
    def set_api_key(self, provider: ProviderType, api_key: str):
        """Set API key for a provider."""
        if provider == ProviderType.OPENAI:
            self.providers[provider] = OpenAIProvider(api_key=api_key)
        elif provider == ProviderType.ANTHROPIC:
            self.providers[provider] = AnthropicProvider(api_key=api_key)
        elif provider == ProviderType.GOOGLE:
            self.providers[provider] = GoogleProvider(api_key=api_key)
        elif provider == ProviderType.GROQ:
            self.providers[provider] = GroqProvider(api_key=api_key)
        elif provider == ProviderType.OPENROUTER:
            self.providers[provider] = OpenRouterProvider(api_key=api_key)
    
    def set_ollama_model(self, model: str):
        """Set Ollama model."""
        self.providers[ProviderType.OLLAMA] = OllamaProvider(model=model)
    
    def set_active_provider(self, provider: ProviderType):
        """Set the active LLM provider."""
        self.active_provider = provider
    
    def get_provider_status(self) -> dict:
        """Get status of all providers."""
        return {
            provider.value: {
                "configured": self.providers[provider].is_configured(),
                "active": provider == self.active_provider,
            }
            for provider in ProviderType
        }
    
    async def generate_code(
        self,
        user_request: str,
        current_code: str = "",
        context: dict = None
    ) -> dict:
        """Generate code using the active provider."""
        provider = self.providers.get(self.active_provider)
        
        if not provider:
            return {"success": False, "code": "", "error": "No provider configured"}
        
        if not provider.is_configured():
            return {
                "success": False,
                "code": "",
                "error": f"{self.active_provider.value} is not configured. Please set API key."
            }
        
        try:
            # Format context
            context_str = self._format_context(context) if context else "No runtime context available"
            
            prompt = DATA_SCIENTIST_CODE_PROMPT.format(
                context=context_str,
                current_code=current_code or "# Empty cell",
                user_request=user_request,
            )
            
            system_prompt = DATA_SCIENTIST_SYSTEM_PROMPT if self.use_data_scientist_persona else None
            
            response = await provider.generate(prompt, system_prompt)
            
            # Clean up code
            code = self._clean_code(response)
            
            return {"success": True, "code": code, "error": None}
        
        except Exception as e:
            return {"success": False, "code": "", "error": str(e)}
    
    def _format_context(self, context: dict) -> str:
        """Format runtime context for prompt."""
        lines = []
        
        variables = context.get("variables", [])
        if variables:
            lines.append("### Variables")
            for v in variables:
                line = f"- {v['name']} ({v['type']})"
                if 'shape' in v:
                    line += f" shape={v['shape']}"
                if 'length' in v:
                    line += f" len={v['length']}"
                lines.append(line)
        
        dataframes = context.get("dataframes", [])
        if dataframes:
            lines.append("\n### DataFrames")
            for df in dataframes:
                lines.append(f"- {df['name']} {df.get('shape', '')}")
                if 'columns' in df:
                    lines.append(f"  Columns: {', '.join(df['columns'][:10])}")

        files = context.get("files", [])
        if files:
            lines.append("\n### Available Files")
            for f in files:
                lines.append(f"- {f} (File)")

        dbs = context.get("database_connections", [])
        if dbs:
            lines.append("\n### Database Connections")
            for db in dbs:
                lines.append(f"- {db['name']} ({db['type']})")
        
        imports = context.get("imports", [])
        if imports:
            lines.append(f"\n### Imports: {', '.join(imports[:10])}")
        
        return "\n".join(lines) if lines else "No context"
    
    def _clean_code(self, response: str) -> str:
        """Clean up code from LLM response."""
        import re
        
        # Try to find markdown code blocks
        code_block_pattern = r"```(?:python)?\s*(.*?)```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            # Return the first code block found
            return matches[0].strip()
        
        # If no code blocks, return the whole response (fallback)
        # But try to strip any leading/trailing backticks just in case
        return response.strip().strip("`")


# Global LLM manager
llm_manager = LLMManager()
