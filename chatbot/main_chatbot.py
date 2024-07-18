import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, "shared")
sys.path.append(parent_dir)

import gradio as gr
from datetime import datetime
from typing import List
from rag import BaseRAG, RAG_MODELS
from loguru import logger

def initiate_logs(log_level="INFO"):
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"{shared_dir}/logs/{current_time}_chatbot.log"
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)

# Global variables
rag_models = RAG_MODELS
current_rag: BaseRAG = None

SUGGESTED_QUESTIONS = [
    "¿Cuál es la capital de Francia?",
    "¿Cuál es el alcance de la Hyundai Kona Electric?",
    "¿Cuáles son las ventajas de la Nissan Kicks comparada con la Changan CS35?",
    "¿Cuántos airbags tiene la Nissan Kicks?"
]

def format_message(role: str, content: str) -> str:
    align = "right" if role == "human" else "left"
    return f"""
    <div class="message {role}" style="display: flex; justify-content: {align};">
        <div style="background-color: #e6f3ff; 
                    color: black;
                    border-radius: 10px; 
                    padding: 10px; 
                    margin: 5px; 
                    max-width: 70%;">
            {content}
        </div>
    </div>
    """

def update_metrics(usage):
    return (
        f"Último: {usage.token_input} tokens de entrada, {usage.token_output} tokens de salida, "
        f"${usage.cost:.4f}, {usage.time:.2f}s\n"
        f"Total: {usage.summarize()[0]} tokens de entrada, {usage.summarize()[1]} tokens de salida, "
        f"${usage.summarize()[2]:.4f}, {usage.summarize()[3]:.2f}s"
    )

def chat(message: str, history: List[List[str]]) -> List:
    response = current_rag.chat(message)
    history.append([message, response])
    return history, current_rag.get_logs(), update_metrics(current_rag.get_usage())

def start_conversation(name: str, model_name: str) -> List:
    global current_rag
    current_rag = next(model for model in rag_models if model.__name__ == model_name)()
    greeting = current_rag.greet(name)
    return [
        [[None, greeting]], 
        current_rag.get_logs(), 
        update_metrics(current_rag.get_usage()),
        gr.update(visible=False),  # Hide start screen
        gr.update(visible=True),   # Show chat interface
    ]

def clear_conversation() -> List:
    global current_rag
    current_rag.reset()
    return [[], current_rag.get_logs(), update_metrics(current_rag.get_usage())]

def restart_conversation() -> List:
    global current_rag
    current_rag = None
    return [
        gr.update(value=""),  # Clear name input
        gr.update(value=None),  # Reset model dropdown
        gr.update(visible=True),  # Show start screen
        gr.update(visible=False),  # Hide chat interface
        [], "", ""  # Clear chat history, logs, and metrics
    ]

def use_suggested_question(question: str, history: List[str]) -> List:
    return chat(question, history)



with gr.Blocks() as demo:
    gr.Markdown("# 🚗🤖 Autobot")
    
    with gr.Column(visible=True) as start_screen:
        name_input = gr.Textbox(label="Tu Nombre", placeholder="Escribe tu nombre aquí...", value="Charlie")
        model_dropdown = gr.Dropdown(choices=[model.__name__ for model in rag_models], label="Selecciona el Modelo RAG")
        start_button = gr.Button("Comenzar")

    with gr.Column(visible=False) as chat_interface:
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(elem_id="chatbot", height=400)
                msg_input = gr.Textbox(label="Mensaje", placeholder="Escribe tu mensaje aquí...")
                send_button = gr.Button("Enviar")
                
                gr.Examples(
                    examples=SUGGESTED_QUESTIONS,
                    inputs=msg_input,
                    label="Preguntas Sugeridas"
                )
                
                with gr.Row():
                    clear_button = gr.Button("Limpiar")
                    restart_button = gr.Button("Reiniciar")
            
            with gr.Column(scale=1):
                logs_display = gr.Textbox(label="Registros", lines=15)
                metrics_display = gr.Textbox(label="Métricas")

    start_button.click(
        start_conversation,
        inputs=[name_input, model_dropdown],
        outputs=[chatbot, logs_display, metrics_display, start_screen, chat_interface]
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
        outputs=[name_input, model_dropdown, start_screen, chat_interface, chatbot, logs_display, metrics_display]
    )

if __name__ == "__main__":
    demo.launch()