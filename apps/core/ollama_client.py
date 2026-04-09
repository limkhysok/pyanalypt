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
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")

    def generate_response(self, prompt, system_prompt=None):
        """
        Sends a prompt to Ollama and returns the full generated text.
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
            raise OllamaError(f"Failed to connect to Ollama: {str(e)}")

    def stream_response(self, prompt, system_prompt=None):
        """
        Streams tokens from Ollama as a generator of plain text chunks.
        Yields each token string as it arrives.
        """
        try:
            kwargs = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            for chunk in ollama.generate(**kwargs):
                token = chunk.response
                if token:
                    yield token
        except Exception as e:
            raise OllamaError(f"Failed to connect to Ollama: {str(e)}")


def analyze_dataset_metadata(columns, sample_stats=None):
    """
    Returns the full AI analysis as a single string (non-streaming).
    """
    client = OllamaClient()
    system_prompt, prompt = _build_prompt(columns, sample_stats)
    return client.generate_response(prompt, system_prompt=system_prompt)


def stream_dataset_analysis(columns, sample_stats=None):
    """
    Yields SSE-formatted data chunks for streaming to the client.
    Format: data: <token>\n\n
    A final data: [DONE]\n\n signals end of stream.
    """
    client = OllamaClient()
    system_prompt, prompt = _build_prompt(columns, sample_stats)

    try:
        for token in client.stream_response(prompt, system_prompt=system_prompt):
            # Escape newlines so SSE stays valid
            safe_token = token.replace("\n", "\\n")
            yield f"data: {safe_token}\n\n"
        yield "data: [DONE]\n\n"
    except OllamaError as e:
        yield f"data: [ERROR] {str(e)}\n\n"


def _build_prompt(columns, sample_stats):
    system_prompt = (
        "You are an expert data analyst. Your task is to look at the column headers "
        "and summary statistics of a dataset and suggest 3-5 'problem statements' "
        "or analysis goals. Be concise and professional."
    )
    prompt = f"Dataset Columns: {', '.join(columns)}\n"
    if sample_stats:
        prompt += f"Summary Statistics: {json.dumps(sample_stats, indent=2)}\n"
    prompt += "\nPlease provide a list of 3-5 problem statements for this dataset."
    return system_prompt, prompt
