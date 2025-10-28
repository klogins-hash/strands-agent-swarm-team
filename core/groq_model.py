"""
Groq API integration for Llama 3.3 70B
Replaces local Ollama with cloud-based Groq API.
"""

import os
import logging
from typing import Dict, List, Any, Optional, AsyncIterator
import json
from groq import Groq
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class GroqModel:
    """Groq API client for Llama 3.3 70B model."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Groq client."""
        try:
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Groq client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False
    ) -> str:
        """Generate text using Groq API."""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._sync_generate,
                messages,
                max_tokens,
                temperature,
                top_p,
                stream
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            raise
    
    def _sync_generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float,
        stream: bool
    ) -> str:
        """Synchronous generation for thread pool execution."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream
            )
            
            if stream:
                # Handle streaming response
                content = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content += chunk.choices[0].delta.content
                return content
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Sync generation error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Chat completion with conversation history."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._sync_chat,
                messages,
                max_tokens,
                temperature,
                top_p
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Groq chat error: {e}")
            raise
    
    def _sync_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Synchronous chat for thread pool execution."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Sync chat error: {e}")
            raise
    
    async def function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[str] = "auto",
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Function calling with Groq API."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._sync_function_call,
                messages,
                functions,
                function_call,
                max_tokens,
                temperature
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Groq function call error: {e}")
            raise
    
    def _sync_function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Synchronous function calling for thread pool execution."""
        try:
            # Note: Function calling may not be available in all Groq models
            # This is a placeholder implementation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                # tools=functions,  # Uncomment when Groq supports function calling
                # tool_choice=function_call
            )
            
            return {
                "content": response.choices[0].message.content,
                "function_call": None  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Sync function call error: {e}")
            raise
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> AsyncIterator[str]:
        """Stream text generation."""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            # Run streaming in thread pool
            loop = asyncio.get_event_loop()
            
            def _stream():
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            
            # Convert sync generator to async
            for chunk in await loop.run_in_executor(self.executor, lambda: list(_stream())):
                yield chunk
                await asyncio.sleep(0)  # Allow other tasks to run
                
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "provider": "groq",
            "model": self.model,
            "max_tokens": 32768,  # Llama 3.3 70B context length
            "supports_function_calling": False,  # Update when available
            "supports_streaming": True,
            "api_key_configured": bool(self.api_key)
        }
    
    async def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            response = await self.generate(
                prompt="Hello",
                max_tokens=10,
                temperature=0.1
            )
            return bool(response)
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False
    
    def close(self):
        """Clean up resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Groq model executor shut down")

# Global model instance
groq_model = None

def get_groq_model() -> GroqModel:
    """Get or create global Groq model instance."""
    global groq_model
    if groq_model is None:
        groq_model = GroqModel()
    return groq_model

def initialize_groq_model(api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile") -> GroqModel:
    """Initialize Groq model with custom parameters."""
    global groq_model
    groq_model = GroqModel(api_key=api_key, model=model)
    return groq_model
