import io
import json
import os
import time
import logging
from datetime import datetime
from typing import Iterable, Optional

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

# define a dictionary to map with assistant name and assistant object
assistant_types = { 'web', 'math' }
personal_assistants = {}

# define a dictionary to map with assistant name, user_id and thread_id, the assistant_name and user_id are the key
personal_assistant_threads = {}

def conversation_internal_with_assistant(client : AzureOpenAI, request_body : any, assistant_type : str, user_id : str, deployment_model : str) :
    # retrieve the assistant or create a new one
    global personal_assistants
    
    try:
        assistant = personal_assistants.get(assistant_type)
        if assistant is None:
            assistant = retrieve_and_create_assistant(client, assistant_type, deployment_model)
            personal_assistants[assistant_type] = assistant
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Handle error appropriately
        return jsonify({"error": str(e)}), 500
    
    # get the user messages and history metadata
    request_messages = request_body["messages"]
    history_metadata = request_body.get("history_metadata", {})

    # get the latest message
    latest_message = request_messages[-1]
    content = latest_message["content"]

    if DEBUG_LOGGING: logging.debug(f"user_id: {user_id}")
    if DEBUG_LOGGING: logging.debug(f"request_body: {request_body}")    
    if DEBUG_LOGGING: logging.debug(f"content: {content}")
    if DEBUG_LOGGING: logging.debug(f"history_metadata: {history_metadata}")

    # retrieve the assistant thread or create a new one
    global personal_assistant_threads

    try:
        # get thread_id from assistant_type and user_id
        newThread = False
        if user_id in personal_assistant_threads and assistant_type in personal_assistant_threads[user_id]:
            thread_id = personal_assistant_threads[user_id][assistant_type]
        else:
            thread_id = None
        if thread_id is None:
            if DEBUG_LOGGING: logging.debug(f"No existing thread found by {user_id} for {assistant_type}")
            newThread = True
        elif len(request_messages) > 1:
            # delete the old thread
            client.beta.threads.delete(thread_id)
            newThread = True
            if DEBUG_LOGGING: logging.debug(f"Deleted the old thread: {thread_id}")

        if newThread:
            thread = client.beta.threads.create()
            thread_id = thread.id
            personal_assistant_threads[user_id] = { assistant_type: thread_id }
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Handle error appropriately
        return jsonify({"error": str(e)}), 500

    # create a new message in the assistant thread
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=content)

    # create a new run in the assistant thread
    run = client.beta.threads.runs.create(
        assistant_id=assistant.id,
        thread_id=thread_id,
        instructions="Please address the user as Jane Doe. The user has a premium account. Be assertive, accurate, and polite. Ask if the user has further questions. "
        + "The current date and time is: "
        + datetime.now().strftime("%x %X")
        + ".",
    )

    if DEBUG_LOGGING: logging.debug(f"processing ...")

    try:
        # poll the run till completion
        poll_run_till_completion(client, thread_id, run.id, {}, 10, 3)

        # retrieve and print messages
        return retrieve_messages_and_respond(client, thread_id, history_metadata)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Handle error appropriately
        return jsonify({"error": str(e)}), 500
    
def retrieve_and_create_assistant(client : AzureOpenAI, assistant_type : str, deployment_model : str) :
    if DEBUG_LOGGING: logging.debug(f"assistant_type: {assistant_type}")

    if assistant_type == "math":
        assistant_name = "Math Tutor"
        assistant_instructions = "You are a personal math tutor. Write and run code to answer math questions."
        code_interpreter_type = "code_interpreter"
    elif assistant_type == "web":
        assistant_name = "Web Assistant"
        assistant_instructions = "You are a personal web assistant. Write and run code to answer web development questions."
        code_interpreter_type = "code_interpreter"

    # retrieve assistants and find the assistant
    assistants = client.beta.assistants.list()
    assistant = None

    for a in assistants:
        if a.name == assistant_name:
            assistant = a
            break

    if assistant is None:
        assistant = client.beta.assistants.create(
            name=assistant_name,
            instructions=assistant_instructions,
            tools=[{"type": code_interpreter_type}],
            model=deployment_model,
        )
        logging.debug(f"{assistant_name}: {assistant}")
    else:
        logging.debug(f"{assistant_name} already exists: {assistant}")

    return assistant

def poll_run_till_completion(
    client: AzureOpenAI,
    thread_id: str,
    run_id: str,
    available_functions: dict,
    max_steps: int = 10,
    wait: int = 3,
) -> None:
    """
    Poll a run until it is completed or failed or exceeds a certain number of iterations (MAX_STEPS)
    with a preset wait in between polls

    @param client: OpenAI client
    @param thread_id: Thread ID
    @param run_id: Run ID
    @param assistant_id: Assistant ID
    @param max_steps: Maximum number of steps to poll
    @param wait: Wait time in seconds between polls

    """

    if (client is None and thread_id is None) or run_id is None:
        if DEBUG_LOGGING: logging.error("Client, Thread ID and Run ID are required.")
        raise Exception("Client, Thread ID and Run ID are required.")
   
    cnt = 0
    while cnt < max_steps:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        
        if DEBUG_LOGGING: logging.debug(f"Poll {cnt}: {run.status}")
        cnt += 1
        if run.status == "requires_action":
            tool_responses = []
            if (
                run.required_action.type == "submit_tool_outputs"
                and run.required_action.submit_tool_outputs.tool_calls is not None
            ):
                tool_calls = run.required_action.submit_tool_outputs.tool_calls

                for call in tool_calls:
                    if call.type == "function":
                        if call.function.name not in available_functions:
                            raise Exception("Function requested by the model does not exist")
                        function_to_call = available_functions[call.function.name]
                        tool_response = function_to_call(**json.loads(call.function.arguments))
                        tool_responses.append({"tool_call_id": call.id, "output": tool_response})

            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_responses
            )
        if run.status == "failed":
            if DEBUG_LOGGING: logging.error("Run failed.")
            raise Exception("Run failed.")
        if run.status == "completed":
            if DEBUG_LOGGING: logging.debug("Run completed.")
            break
        time.sleep(wait)

def retrieve_messages_and_respond(
    client: AzureOpenAI, thread_id: str, history_metadata: dict
) -> any:
    """
    Retrieve a list of messages in a thread and print it out with the query and response

    @param client: OpenAI client
    @param thread_id: Thread ID
    @param verbose: Print verbose output
    @param out_dir: Output directory to save images
    @return: Messages object

    """

    if client is None and thread_id is None:
        print("Client and Thread ID are required.")
        raise Exception("Client and Thread ID are required.")
    
    messages = client.beta.threads.messages.list(thread_id=thread_id)

    for message in messages:
        if message.role == "assistant":
            break

    assistantContent = ""
    for item in message.content:
        # Determine the content type
        if isinstance(item, MessageContentText):
            if DEBUG_LOGGING: logging.debug(f"{message.role}:\n{item.text.value}\n")
            assistantContent += item.text.value
        elif isinstance(item, MessageContentImageFile):
            # Retrieve image from file id
            response_content = client.files.content(item.image_file.file_id)
            data_in_bytes = response_content.read()

            # save image to file
            with open(f"./images/{thread_id}.jpg", "wb") as img_file:
                img_file.write(data_in_bytes)

            if DEBUG_LOGGING: logging.debug(f"Image saved to file: ./images/{thread_id}.jpg")
            
            assistantContent += f"<img src=\"./images/{thread_id}.jpg\" alt=\"Example image\" width=\"100%\" height=\"auto\" display=\"block\" />"
    
    if DEBUG_LOGGING: logging.debug(f"Assistant:\n{assistantContent}\n")

    response_obj = {
        "id": message.id,
        "model": "gpt-3.5-turbo",
        "created": message.created_at,
        "object": message.object,
        "choices": [{
            "messages": [{
                "role": message.role,
                "content": assistantContent
            }]
        }],
        "history_metadata": history_metadata
    }

    return jsonify(response_obj), 200
