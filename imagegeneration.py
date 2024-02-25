import os
import logging
import uuid
from openai import AzureOpenAI
import json
from flask import jsonify

# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
DEBUG_LOGGING = DEBUG.lower() == "true"
if DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

def conversation_internal_with_dalle(client : AzureOpenAI, request_body : any, deployment_model : str) :
    # get the user messages and history metadata
    request_messages = request_body["messages"]
    history_metadata = request_body.get("history_metadata", {})

    # get the latest message
    latest_message = request_messages[-1]
    content = latest_message["content"]

    # logging.error(f"request_body: {request_body}")    
    logging.error(f"content: {content}")
    logging.error(f"history_metadata: {history_metadata}")

    result = client.images.generate(
        model="Dalle3", # the name of your DALL-E 3 deployment
        prompt=content,
        n=1
    )

    logging.error(f"result: {result}")

    image_url = json.loads(result.model_dump_json())['data'][0]['url']

    assistantContent = f"Here is an image generated from your prompt:"

    assistantContent += f"<img src=\"{image_url}\" alt=\"Example image\" width=\"100%\" height=\"auto\" display=\"block\" />"

    response_obj = {
        "id": str(uuid.uuid4()),
        "model": "gpt-3.5-turbo",
        "created": result.created,
        "choices": [{
            "messages": [{
                "role": "assistant",
                "content": assistantContent
            }]
        }],
        "history_metadata": history_metadata
    }

    return jsonify(response_obj), 200