import os
import json
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

async def get_completion(messages: List[Dict[str, Any]], model: str = "gpt-4o", temperature: float = 0.7, response_format: Dict[str, str] = None) -> Dict[str, Any]:
    """Get a completion from OpenAI API"""
    try:
        client = AsyncOpenAI()
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            kwargs["response_format"] = response_format
            
        response = await client.chat.completions.create(**kwargs)
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logging.error(f"Error getting completion: {str(e)}")
        return {"error": str(e)}

async def get_llm(model: str = "gpt-4o", temperature: float = 0.7, response_format: Dict[str, str] = None) -> Any:
    """Get an LLM instance configured with the specified parameters"""
    async def llm(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        return await get_completion(messages, model, temperature, response_format)
    return llm 