import os 
import json
from typing import Any , List , Optional


from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM


ANTHROPIC_MODEL = "claud-sonnet-4-6"

class AnthropicLLM(LLM):
    model: str = ANTHROPIC_MODEL
    api_key : Optional[str] = None
    max_tokens : int = 200

    def __init__(self , **data : Any):
        super().__init__(**data)

        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; cannot use AnthropicLLM.")
    
    @property
    def _llm_type(self)->str:
        return "anthropic-custom here"
    
    def _call(
        self , 
        prompt: str , 
        stop = None , )->str:

        body = json.jump(
            {
                "model":self.model ,
                "max_tokens":self.max_tokens ,
                "messages":[{"role": "user", "content": prompt}],
            }
        ).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)

        text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        if stop:
            for s in stop:
                text = text.split(s)[0]
                
        return text



