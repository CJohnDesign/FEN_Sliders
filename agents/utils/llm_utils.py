import asyncio
import json
import base64
import logging
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from openai import AsyncOpenAI
from ..config.settings import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    OPENAI_ORG_ID,
    DEFAULT_MODEL,
    TEMPERATURE
)

# Set up logging
logging.basicConfig(
    filename='builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler for more visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

async def get_completion(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Get a completion from the LLM"""
    if model.startswith('claude'):
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=TEMPERATURE,
                system="You are a helpful AI assistant that processes summaries and generates structured content. Your responses should be valid JSON arrays when processing summaries.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            # Convert TextBlock to string and log
            content = str(response.content[0].text) if hasattr(response.content[0], 'text') else str(response.content)
            logging.info(f"Anthropic API response preview: {content[:200]}...")
            return content
        except Exception as e:
            logging.error(f"Error getting completion from Anthropic: {str(e)}")
            raise
    else:
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            organization=OPENAI_ORG_ID
        )
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error getting completion from OpenAI: {str(e)}")
            raise

def encode_image(image_path):
    """Convert an image file to base64 encoding"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_llm(model: str = DEFAULT_MODEL, vision: bool = False):
    """Get the appropriate LLM based on the model name and requirements"""
    
    if vision:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in environment")
            
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            organization=OPENAI_ORG_ID,
            timeout=30.0,
            max_retries=3
        )
        
        async def vision_llm(messages):
            try:
                api_messages = []
                
                for msg in messages:
                    if isinstance(msg.get("content"), list):
                        content = []
                        for item in msg["content"]:
                            if isinstance(item, str):
                                content.append({"type": "text", "text": item})
                            elif isinstance(item, dict) and "image_url" in item:
                                image_url = item["image_url"]
                                # If it's already a data URL, use it directly
                                if image_url.startswith("data:image"):
                                    content.append({
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_url,
                                            "detail": "low"  # Use low detail for faster processing
                                        }
                                    })
                                else:
                                    # Treat it as a file path
                                    try:
                                        base64_image = encode_image(image_url)
                                        content.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/jpeg;base64,{base64_image}",
                                                "detail": "low"  # Use low detail for faster processing
                                            }
                                        })
                                    except Exception as e:
                                        logging.error(f"Failed to encode image: {str(e)}")
                                        raise
                        api_messages.append({
                            "role": msg["role"],
                            "content": content
                        })
                    else:
                        api_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = await client.chat.completions.create(
                            model="gpt-4o",
                            messages=api_messages,
                            temperature=TEMPERATURE,
                            response_format={"type": "json_object"},
                            max_tokens=1000  # Reduced token count for faster response
                        )
                        # Parse the JSON content from the message
                        message = response.choices[0].message
                        try:
                            # Only log a preview of the content
                            preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                            logging.info(f"API response preview: {preview}")
                            content = json.loads(message.content)
                            if not isinstance(content, dict) or "title" not in content:
                                logging.error("Invalid response format. Expected object with 'title' field.")
                                content = {
                                    "title": "Error: Invalid Response",
                                    "summary": "The API response was not in the expected format",
                                    "feature_category": None,
                                    "hasTable": False
                                }
                            return {
                                "role": message.role,
                                "content": content
                            }
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse JSON response: {e}")
                            raise
                    except Exception as e:
                        error_msg = str(e)
                        logging.error(f"Vision API error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                        
                        if "rate limit" in error_msg.lower():
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                logging.info(f"Rate limited. Waiting {wait_time}s before retry...")
                                await asyncio.sleep(wait_time)
                                continue
                        elif "invalid_api_key" in error_msg:
                            logging.error("Invalid API key")
                            raise
                        elif attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logging.info(f"Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        raise  # Re-raise the last error if we've exhausted retries
                        
            except Exception as e:
                logging.error(f"Unhandled error in vision API: {str(e)}")
                raise
            
        return vision_llm
    
    if model.startswith("gpt"):
        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            organization=OPENAI_ORG_ID,
            model=model,
            temperature=TEMPERATURE
        )
    elif model.startswith("claude"):
        return ChatAnthropic(
            api_key=ANTHROPIC_API_KEY,
            model=model,
            temperature=TEMPERATURE
        )
    else:
        raise ValueError(f"Unsupported model: {model}") 