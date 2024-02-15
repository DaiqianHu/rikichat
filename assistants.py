import io
import os
import time
import logging
from datetime import datetime
from typing import Iterable

from openai import AzureOpenAI
from openai.types.beta.threads.message_content_image_file import MessageContentImageFile
from openai.types.beta.threads.message_content_text import MessageContentText
from openai.types.beta.threads.messages import MessageFile
from PIL import Image
from flask import jsonify

# Debug settings
DEBUG = os.environ.get("DEBUG", "false")
DEBUG_LOGGING = DEBUG.lower() == "true"
if DEBUG_LOGGING:
    logging.basicConfig(level=logging.DEBUG)

MathAssistant = None
MathAssistantThread = None

def process_message(client, content: str, history_metadata) -> None:
    client.beta.threads.messages.create(thread_id=MathAssistantThread.id, role="user", content=content)
    run = client.beta.threads.runs.create(
        thread_id=MathAssistantThread.id,
        assistant_id=MathAssistant.id,
        instructions="Please address the user as Jane Doe. The user has a premium account. Be assertive, accurate, and polite. Ask if the user has further questions. "
        + "The current date and time is: "
        + datetime.now().strftime("%x %X")
        + ".",
    )

    if DEBUG_LOGGING: logging.debug(f"processing ...")

    while True:
        run = client.beta.threads.runs.retrieve(thread_id=MathAssistantThread.id, run_id=run.id)
        if run.status == "completed":
            # Handle completed
            messages = client.beta.threads.messages.list(thread_id=MathAssistantThread.id)

            for message in messages:
                if message.role == "assistant":
                    break

            response_obj = {
                "id": message.id,
                "model": "gpt-3.5-turbo",
                "created": message.created_at,
                "object": message.object,
                "choices": [{
                    "messages": [{
                        "role": message.role,
                        "content": message.content[0].text.value
                    }]
                }],
                "history_metadata": history_metadata
            }

            return jsonify(response_obj), 200
            # format_messages(messages)     
        if run.status == "failed":
            messages = client.beta.threads.messages.list(thread_id=MathAssistantThread.id)
            answer = messages.data[0].content[0].text.value
            if DEBUG_LOGGING: logging.debug(f"Failed User:\n{content}\nAssistant:\n{answer}\n")
            # Handle failed
            break
        if run.status == "expired":
            # Handle expired
            if DEBUG_LOGGING: logging.debug(run)
            break
        if run.status == "cancelled":
            # Handle cancelled
            if DEBUG_LOGGING: logging.debug(run)
            break
        if run.status == "requires_action":
            # Handle function calling and continue processing
            pass
        else:
            time.sleep(5)

def format_messages(client, messages: Iterable[MessageFile]) -> None:
    message_list = []

    # Get all the messages till the last user message
    for message in messages:
        message_list.append(message)
        if message.role == "user":
            break

    # Reverse the messages to show the last user message first
    message_list.reverse()

    # print the user or Assistant messages or images
    for message in message_list:
        for item in message.content:
            # Determine the content type
            if isinstance(item, MessageContentText):
                if DEBUG_LOGGING: logging.debug(f"{message.role}:\n{item.text.value}\n")
            elif isinstance(item, MessageContentImageFile):
                # Retrieve image from file id
                response_content = client.files.content(item.image_file.file_id)
                data_in_bytes = response_content.read()
                # Convert bytes to image
                readable_buffer = io.BytesIO(data_in_bytes)
                image = Image.open(readable_buffer)
                # Resize image to fit in terminal
                width, height = image.size
                image = image.resize((width // 2, height // 2), Image.LANCZOS)
                # Display image
                image.show()

def conversation_internal_with_math_assistant(client : AzureOpenAI, request_body : any, deploymentModel : str) :
    request_messages = request_body["messages"]

    # get the latest message
    latest_message = request_messages[-1]
    content = latest_message["content"]

    global MathAssistant
    global MathAssistantThread

    if DEBUG_LOGGING: logging.debug(f"content: {content}")

    if MathAssistant is None:
        MathAssistant = client.beta.assistants.create(
            name="Math Tutor",
            instructions="You are a personal math tutor. Write and run code to answer math questions.",
            tools=[{"type": "code_interpreter"}],
            model=deploymentModel,
        )
        if DEBUG_LOGGING: logging.debug(f"MathAssistant: {MathAssistant}")
    else:
        if DEBUG_LOGGING: logging.debug(f"MathAssistant already exists: {MathAssistant}")

    if MathAssistantThread is None:
        MathAssistantThread = client.beta.threads.create()
        if DEBUG_LOGGING: logging.debug(f"MathAssistantThread: {MathAssistantThread}")
    else:
        if DEBUG_LOGGING: logging.debug(f"MathAssistantThread already exists: {MathAssistantThread}")

    history_metadata = request_body.get("history_metadata", {})

    return process_message(client, content, history_metadata)
