from enum import Enum
from typing import AsyncIterator, Dict, List, Literal, Optional

import bittensor as bt
import pydantic
from starlette.responses import StreamingResponse

from ..providers.image import DallE, Stability

from ..providers.text import Anthropic, GeminiPro, OpenAI


class IsAlive( bt.Synapse ):
    answer: Optional[str] = None
    completion: str = pydantic.Field(
        "",
        title="Completion",
        description="Completion status of the current StreamPrompting object. "
                    "This attribute is mutable and can be updated.",
    )

class ImageResponse(bt.Synapse):
    """ A class to represent the response for an image-related request. """

    completion: Optional[Dict] = pydantic.Field(
        None,
        title="Completion",
        description="The completion data of the image response."
    )

    messages: str = pydantic.Field(
        ...,
        title="Messages",
        description="Messages related to the image response."
    )

    class Provider(str, Enum):
        """ A class to represent the provider options for the StreamPrompting object. """
        dalle = DallE.__name__
        stability = Stability.__name__

    provider: Provider = pydantic.Field(
        Provider.dalle,
        title="provider",
        description="The provider to use when calling for your response.",
    )


    model: str = pydantic.Field(
        ...,
        title="Model",
        description="The model used for generating the image."
    )

    style: str = pydantic.Field(
        ...,
        title="Style",
        description="The style of the image."
    )

    size: str = pydantic.Field(
        ...,
        title="Size",
        description="The size of the image."
    )

    quality: str = pydantic.Field(
        ...,
        title="Quality",
        description="The quality of the image."
    )

    required_hash_fields: List[str] = pydantic.Field(
        ["messages"],
        title="Required Hash Fields",
        description="A list of fields required for the hash."
    )

    def deserialize(self) -> Optional[Dict]:
        """ Deserialize the completion data of the image response. """
        return self.completion

class Embeddings( bt.Synapse):
    """ A class to represent the embeddings request and response. """

    texts: List[str] = pydantic.Field(
        ...,
        title="Text",
        description="The list of input texts for which embeddings are to be generated."
    )

    model: str = pydantic.Field(
        "text-embedding-ada-002",
        title="Model",
        description="The model used for generating embeddings."
    )

    embeddings: Optional[List[List[float]]] = pydantic.Field(
        None,
        title="Embeddings",
        description="The resulting list of embeddings, each corresponding to an input text."
    )

class StreamPrompting(bt.StreamingSynapse):

    messages: List[Dict[str, str]] = pydantic.Field(
        ...,
        title="Messages",
        description="A list of messages in the StreamPrompting scenario, "
                    "each containing a role and content. Immutable.",
        allow_mutation=False,
    )

    required_hash_fields: List[str] = pydantic.Field(
        ["messages"],
        title="Required Hash Fields",
        description="A list of required fields for the hash.",
        allow_mutation=False,
    )

    seed: int = pydantic.Field(
        "",
        title="Seed",
        description="Seed for text generation. This attribute is immutable and cannot be updated.",
    )

    temperature: float = pydantic.Field(
        0.0,
        title="Temperature",
        description="Temperature for text generation. "
                    "This attribute is immutable and cannot be updated.",
    )

    completion: str = pydantic.Field(
        "",
        title="Completion",
        description="Completion status of the current StreamPrompting object. "
                    "This attribute is mutable and can be updated.",
    )

    class Provider(str, Enum):
        """ A class to represent the provider options for the StreamPrompting object. """
        openai = OpenAI.__name__
        anthropic = Anthropic.__name__
        gemini_pro = GeminiPro.__name__

    provider: Provider = pydantic.Field(
        Provider.openai,
        title="provider",
        description="The provider to use when calling for your response.",
    )

    model: str = pydantic.Field(
        "",
        title="model",
        description="The model to use when calling provider for your response.",
    )

    async def process_streaming_response(self, response: StreamingResponse) -> AsyncIterator[str]:
        if self.completion is None:
            self.completion = ""
        async for chunk in response.content.iter_any():
            tokens = chunk.decode("utf-8")
            for token in tokens:
                if token:
                    self.completion += token
            yield tokens

    def deserialize(self) -> str:
        return self.completion

    def extract_response_json(self, response: StreamingResponse) -> dict:
        headers = {
            k.decode("utf-8"): v.decode("utf-8")
            for k, v in response.__dict__["_raw_headers"]
        }

        def extract_info(prefix: str) -> dict[str, str]:
            return {
                key.split("_")[-1]: value
                for key, value in headers.items()
                if key.startswith(prefix)
            }

        return {
            "name": headers.get("name", ""),
            "timeout": float(headers.get("timeout", 0)),
            "total_size": int(headers.get("total_size", 0)),
            "header_size": int(headers.get("header_size", 0)),
            "dendrite": extract_info("bt_header_dendrite"),
            "axon": extract_info("bt_header_axon"),
            "messages": self.messages,
            "completion": self.completion,
        }
