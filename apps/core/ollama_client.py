import json
import ollama
from django.conf import settings


class OllamaError(Exception):
    """Custom exception for Ollama client errors."""
    pass


class OllamaClient:
    """
    Client for interacting with a local Ollama instance using the official library.
    """

    def __init__(self, model=None):
        self.model = model or getattr(settings, "OLLAMA_MODEL", "llama3")
        print(f"DEBUG: Using Ollama model: {self.model}")

    def generate_response(self, prompt, system_prompt=None):
        """
        Sends a prompt to Ollama and returns the generated text.
        """
        try:
            kwargs = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = ollama.generate(**kwargs)
            return response.response
        except Exception as e:
            # Re-raise with a custom error
            raise OllamaError(f"Failed to connect to Ollama: {str(e)}")


def analyze_dataset_metadata(columns, sample_stats=None):
    """
    Higher-level utility to analyze dataset metadata using Ollama.
    """
    client = OllamaClient()

    system_prompt = (
        "You are an expert data analyst. Your task is to look at the column headers "
        "and summary statistics of a dataset and suggest 3-5 'problem statements' "
        "or analysis goals. Be concise and professional."
    )

    prompt = f"Dataset Columns: {', '.join(columns)}\n"
    if sample_stats:
        prompt += f"Summary Statistics: {json.dumps(sample_stats, indent=2)}\n"
    
    prompt += "\nPlease provide a list of 3-5 problem statements for this dataset."

    return client.generate_response(prompt, system_prompt=system_prompt)
