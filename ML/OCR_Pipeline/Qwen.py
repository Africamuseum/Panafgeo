import math
import json
import httpx
from ML.utils.utils import setup_response
from ML.utils.status import Status


class Qwen:
    def __init__(self, url, model, prompt, params, max_tokens=4096, temperature=0.0):
        self.url = url
        self.model = model
        self.prompt = prompt
        self.params = params
        self.max_tokens = max_tokens
        self.temperature = temperature

    def compute_avg_logprobs_score(self, logprobs):
        if not logprobs:
            raise ValueError("No logprobs returned by the server")
        logprobs_sum = 0
        for token in logprobs:
            logprobs_sum += token["logprob"]
        return math.exp(logprobs_sum / len(logprobs))

    async def extract_text(self, client, img_path, url64):
        extracted_data = setup_response(img_path, self.model.split("/")[-1], self.params)
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {"type": "image_url", "image_url": {"url": url64}}
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "logprobs": True,
            }
            response = await client.post(self.url, json=payload)

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                extracted_data["error"] = f"Invalid JSON output: {e}"
                extracted_data["status"] = Status.ERR
                return extracted_data

            error = data.get("error")
            if error:
                extracted_data["error"] = error.get("message", "Unknown API error")
                extracted_data["status"] = Status.ERR
                return extracted_data
    
            choices = data.get("choices")
            if not choices:
                extracted_data["error"] = "No choices returned in response"
                extracted_data["status"] = Status.ERR
                return extracted_data
    
            choice = data["choices"][0]
            text = choice["message"]["content"].strip()
            if not text:
                extracted_data["error"] = "Empty response from model"
                extracted_data["status"] = Status.ERR
                return extracted_data

            logprobs_content = choice.get("logprobs")
            logprobs = logprobs_content["content"] if logprobs_content else []
            avg_logprobs = self.compute_avg_logprobs_score(logprobs)
            
            extracted_data["text"] = text
            extracted_data["score"] = avg_logprobs
            if avg_logprobs >= 0.8:
                extracted_data["status"] = Status.SUCCEED
            elif avg_logprobs < 0.8 and avg_logprobs >= 0.6:
                extracted_data["status"] = Status.NEEDS_REVIEW
            else:
                extracted_data["status"] = Status.FAILED
            return extracted_data
        except httpx.TimeoutException:
            extracted_data["error"] = "Request timed out"
            extracted_data["status"] = Status.ERR
            return extracted_data
        except httpx.HTTPError as e:
            extracted_data["error"] = f"HTTP error: {e}"
            extracted_data["status"] = Status.ERR
            return extracted_data
        except ValueError as e:
            extracted_data["error"] = f"Invalid response: {e}"
            extracted_data["status"] = Status.ERR
            return extracted_data
        except Exception as e:
            extracted_data["error"] = f"Unexpected error: {e}"
            extracted_data["status"] = Status.ERR
            return extracted_data