import os
import sys
# Add the shared directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, "shared")
sys.path.append(parent_dir)

import gradio as gr
from datetime import datetime
from typing import List
from rag import BaseRAG, RAG_MODELS
from loguru import logger


def initiate_logs(log_level = "INFO"):
    # Configure loguru
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"{shared_dir}/logs/{current_time}_chatbot.log"
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)
    

# Global variables
rag_models = RAG_MODELS
current_rag: BaseRAG = None

# Helper functions
def format_message(role: str, content: str) -> str:
    return f"<div class='{role}'><strong>{role.capitalize()}:</strong> {content}</div>"

def update_metrics(usage):
    return (
        f"Latest: {usage.token_input} input, {usage.token_output} output tokens, "
        f"${usage.cost:.4f}, {usage.time:.2f}s\n"
        f"Total: {usage.summarize()[0]} input, {usage.summarize()[1]} output tokens, "
        f"${usage.summarize()[2]:.4f}, {usage.summarize()[3]:.2f}s"
    )

# Gradio component update functions
def greet(name: str, model_name: str) -> List:
    global current_rag
    current_rag = next(model for model in rag_models if model.__name__ == model_name)()
    greeting = current_rag.greet(name)
    chat_history = [format_message("assistant", greeting)]
    return [chat_history, current_rag.get_logs(), update_metrics(current_rag.get_usage()), gr.update(visible=True), gr.update(visible=True)]

def chat(message: str, history: List[str]) -> List:
    response = current_rag.chat(message)
    history.append(format_message("human", message))
    history.append(format_message("assistant", response))
    return [history, current_rag.get_logs(), update_metrics(current_rag.get_usage())]

def clear_conversation() -> List:
    global current_rag
    current_rag.reset()
    return [[], current_rag.get_logs(), update_metrics(current_rag.get_usage())]

def restart_conversation() -> List:
    global current_rag
    current_rag = None
    return [
        gr.update(value="Charlie"), 
        gr.Dropdown.update(choices=[model.__name__ for model in rag_models], value=None),
        [], "", "", 
        gr.update(visible=False), 
        gr.update(visible=False)
    ]

# Gradio interface
with gr.Blocks(css="#chatbot {height: 400px; overflow-y: scroll;}") as demo:
    gr.Markdown("# Autobot RAG Chatbot")
    
    with gr.Row():
        name_input = gr.Textbox(label="Your Name", value="Charlie")
        model_dropdown = gr.Dropdown(choices=[model.__name__ for model in rag_models], label="Select RAG Model")
    
    start_button = gr.Button("Start Conversation")

    chatbot = gr.HTML(elem_id="chatbot")
    msg_input = gr.Textbox(label="Message", placeholder="Type your message here...")
    send_button = gr.Button("Send", visible=False)

    logs_display = gr.Textbox(label="Logs", lines=5)
    metrics_display = gr.Textbox(label="Metrics")

    clear_button = gr.Button("Clear", visible=False)
    restart_button = gr.Button("Restart")

    # Event handlers
    start_button.click(
        greet,
        inputs=[name_input, model_dropdown],
        outputs=[chatbot, logs_display, metrics_display, send_button, clear_button]
    )

    send_button.click(
        chat,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, logs_display, metrics_display]
    ).then(lambda: "", outputs=msg_input)

    msg_input.submit(
        chat,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, logs_display, metrics_display]
    ).then(lambda: "", outputs=msg_input)

    clear_button.click(
        clear_conversation,
        outputs=[chatbot, logs_display, metrics_display]
    )

    restart_button.click(
        restart_conversation,
        outputs=[name_input, model_dropdown, chatbot, logs_display, metrics_display, send_button, clear_button]
    )

if __name__ == "__main__":
    demo.launch()