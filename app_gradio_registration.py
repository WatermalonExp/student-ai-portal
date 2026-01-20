import gradio as gr
from ai import ask_llm
from db import init_db, log_chat
import registration

init_db()
registration.init()

def chat_fn(message, history):
    answer = ask_llm(message)
    log_chat(message, answer)
    return answer

def do_register(full_name, email, level, programme, notes):
    try:
        student_id = registration.register_student(full_name, email, level, programme, notes or "")
        return f"✅ Registered! Your Student ID is: {student_id}"
    except Exception as e:
        return f"❌ Registration failed: {e}"

def do_upload(student_id, doc_type, file_obj):
    try:
        if not student_id:
            return "❌ Please enter a Student ID."
        if file_obj is None:
            return "❌ Please choose a file to upload."
        saved = registration.save_uploaded_file(int(student_id), doc_type, file_obj.name)
        return f"✅ Uploaded and saved to: {saved}"
    except Exception as e:
        return f"❌ Upload failed: {e}"

def show_docs(student_id):
    try:
        rows = registration.get_documents(int(student_id))
        if not rows:
            return "No documents found."
        return "\n".join([f"- {dt} | {fn} | {ts}" for (dt, fn, ts) in rows])
    except Exception as e:
        return f"❌ Could not load documents: {e}"

def programme_choices(level):
    if level == "Bachelor":
        return gr.Dropdown(choices=registration.BACHELOR_PROGRAMMES, value=None)
    return gr.Dropdown(choices=registration.MASTER_PROGRAMMES, value=None)

with gr.Blocks(title="Student Registration + AI Assistant (Beta)") as demo:
    gr.Markdown("# 🎓 Student Registration + AI Assistant (Beta)")

    with gr.Tab("AI Chat"):
        gr.ChatInterface(fn=chat_fn, title="Admissions Assistant")

    with gr.Tab("Register"):
        full_name = gr.Textbox(label="Full Name")
        email = gr.Textbox(label="Email")

        level = gr.Radio(choices=["Bachelor", "Master"], value="Bachelor", label="Programme Level")
        programme = gr.Dropdown(choices=registration.BACHELOR_PROGRAMMES, label="Programme")

        level.change(programme_choices, inputs=[level], outputs=[programme])

        notes = gr.Textbox(label="Notes (optional)")
        register_btn = gr.Button("Register")
        register_out = gr.Textbox(label="Result", interactive=False)
        register_btn.click(do_register, [full_name, email, level, programme, notes], register_out)

    with gr.Tab("Upload Documents"):
        student_id = gr.Textbox(label="Student ID")
        doc_type = gr.Dropdown(choices=registration.DOC_TYPES, label="Document Type")
        file_obj = gr.File(label="Choose file")
        upload_btn = gr.Button("Upload")
        upload_out = gr.Textbox(label="Result", interactive=False)
        upload_btn.click(do_upload, [student_id, doc_type, file_obj], upload_out)

        gr.Markdown("## Uploaded documents for a student")
        refresh_btn = gr.Button("Refresh List")
        docs_out = gr.Textbox(label="Documents", lines=8, interactive=False)
        refresh_btn.click(show_docs, [student_id], docs_out)

demo.launch(share=True)
