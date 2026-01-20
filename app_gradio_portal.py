import os
import shutil
import re
import gradio as gr

from models_db import init_db_all
import auth
import applications

from ai import ask_llm
from intents import detect_intent
from programmes import (
    BACHELOR_PROGRAMMES,
    MASTER_PROGRAMMES,
    REQUIRED_DOCS_BACHELOR,
    REQUIRED_DOCS_MASTER,
)
from portal_tools import (
    list_my_applications,
    application_summary,
    delete_all_docs_for_application,
    delete_doc_by_id,
)

# =========================
# INIT
# =========================
init_db_all()
UPLOAD_ROOT = "uploads"


# =========================
# Helpers
# =========================
def required_docs_for(level: str):
    return REQUIRED_DOCS_BACHELOR if level == "Bachelor" else REQUIRED_DOCS_MASTER


def degrees_markdown():
    b = "\n".join([f"- {x}" for x in BACHELOR_PROGRAMMES])
    m = "\n".join([f"- {x}" for x in MASTER_PROGRAMMES])
    return f"## Bachelor’s Study Programmes\n{b}\n\n## Master’s Study Programmes\n{m}"


def update_programmes(level: str):
    return gr.update(
        choices=BACHELOR_PROGRAMMES if level == "Bachelor" else MASTER_PROGRAMMES,
        value=None,
    )

def requirements_md(level: str, programme: str):
    if not programme:
        return "Select a programme to see the typical required documents."
    req = required_docs_for(level)
    bullets = "\n".join([f"- {x}" for x in req])
    return f"### Typical required documents for **{programme}** ({level})\n{bullets}"

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def get_uploaded_doc_types(app_id: int):
    docs = applications.list_documents(int(app_id))
    return {d[1] for d in docs}  # doc_type


def compute_progress_and_status(app_id: int, level: str):
    req = required_docs_for(level)
    uploaded = get_uploaded_doc_types(int(app_id))
    missing = [x for x in req if x not in uploaded]
    progress_text = f"{len(uploaded)}/{len(req)} documents uploaded"
    computed_status = "Complete" if len(missing) == 0 else "In Progress"
    return progress_text, computed_status, missing


# =========================
# PUBLIC AI
# =========================
def ai_public_answer(question: str, level: str, programme: str):
    question = (question or "").strip()
    if not question:
        return "Please type a question."

    injected = ""
    if level in {"Bachelor", "Master"} and programme:
        injected = (
            f"\nProgramme:\n"
            f"- Level: {level}\n"
            f"- Name: {programme}\n"
            f"- Typical required documents: {', '.join(required_docs_for(level))}\n"
        )

    prompt = (
        "You are an admissions assistant. Answer clearly and practically.\n"
        "If asked about document requirements, use the typical checklist provided.\n"
        f"{injected}\nUser question: {question}\nAssistant:"
    )
    return ask_llm(prompt)


# =========================
# AUTH wrappers
# =========================
def do_register(full_name: str, email: str, password: str):
    try:
        uid = auth.register_user(full_name, email, password)
        return "✅ Registered and logged in.", uid
    except Exception as e:
        return f"❌ Register failed: {e}", None


def do_login(email: str, password: str):
    try:
        uid = auth.login_user(email, password)
        return "✅ Logged in.", uid
    except Exception as e:
        return f"❌ Login failed: {e}", None


# =========================
# Dashboard (student)
# =========================
def refresh_apps(user_id):
    if not user_id:
        return "Not logged in.", [], gr.update(choices=[], value=None)

    rows = applications.list_applications(int(user_id))
    table = [[app_id, lvl, name, status, ts] for app_id, lvl, name, status, ts in rows]
    choices = [(f"[{lvl}] {name} — {status}", app_id) for app_id, lvl, name, status, ts in rows]
    dd = gr.update(choices=choices, value=(choices[0][1] if choices else None))
    return f"Found {len(rows)} application(s).", table, dd


def apply_create(user_id, level, programme):
    if not user_id:
        return "❌ Please log in first.", None

    if level == "Bachelor" and programme not in BACHELOR_PROGRAMMES:
        return "❌ Invalid Bachelor programme.", None
    if level == "Master" and programme not in MASTER_PROGRAMMES:
        return "❌ Invalid Master programme.", None

    try:
        app_id = applications.create_application(int(user_id), level, programme)
        return f"✅ Application created: {app_id}", app_id
    except Exception as e:
        return f"❌ Could not create application: {e}", None


# =========================
# Application page (student)
# =========================
def docs_text_and_delete_choices(user_id, app_id):
    if not user_id or not app_id:
        return "No documents loaded.", gr.update(choices=[], value=None)

    docs = applications.list_documents(int(app_id))
    if not docs:
        return "No documents uploaded yet.", gr.update(choices=[], value=None)

    lines = []
    choices = []
    for doc_id, doc_type, fname, saved_path, ts in docs:
        lines.append(f"- [{doc_id}] {doc_type} | {fname} | {ts}")
        choices.append((f"{doc_type} — {fname}", doc_id))

    return "\n".join(lines), gr.update(choices=choices, value=(choices[0][1] if choices else None))


def load_application(user_id, app_id):
    if not user_id or not app_id:
        return (
            "Select an application from the dropdown.",
            "—", "—", "—",
            gr.update(choices=[], value=None),
            "",
            "No documents loaded.",
            gr.update(choices=[], value=None),
            "",
            "",  # student_note
            gr.update(visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )

    row = applications.read_application(int(app_id))
    if not row:
        return (
            "Application not found.",
            "—", "—", "—",
            gr.update(choices=[], value=None),
            "",
            "No documents loaded.",
            gr.update(choices=[], value=None),
            "",
            "",
            gr.update(visible=False),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )

    level, name, status_db = row
    progress_text, computed_status, _missing = compute_progress_and_status(int(app_id), level)

    if status_db != "Submitted":
        status = computed_status
        applications.update_application_status(int(app_id), status)
    else:
        status = "Submitted"

    req = required_docs_for(level)
    docs_txt, delete_dd = docs_text_and_delete_choices(user_id, app_id)

    latest_row = applications.get_latest_decision_row(int(app_id))
    if latest_row:
        decision_ts, decision_status, decision_note, _admin_id = latest_row
        note_text = (decision_note or "").strip()
        if note_text:
            student_note = f"[{decision_ts}] {decision_status}: {note_text}"
        else:
            student_note = f"[{decision_ts}] {decision_status}: (no note)"
    else:
        student_note = ""

    summary = (
        f"### Application #{app_id}\n"
        f"**Level:** {level}\n\n"
        f"**Programme:** {name}\n\n"
        f"**Progress:** {progress_text}\n\n"
        f"**Status:** {status}"
    )

    show_submit = (status == "Complete")
    locked = (status == "Submitted")

    return (
        summary,
        level,
        name,
        status,
        gr.update(choices=req, value=(req[0] if req else None)),
        "",
        docs_txt,
        delete_dd,
        "",
        student_note,
        gr.update(visible=show_submit),
        gr.update(interactive=(not locked)),
        gr.update(interactive=(not locked)),
        gr.update(interactive=(not locked)),
        gr.update(interactive=(not locked)),
        gr.update(interactive=(not locked)),
    )


def upload_doc(user_id, app_id, doc_type, file_obj):
    try:
        if not user_id:
            return "Not logged in."
        if not app_id:
            return "Select an application first."
        if file_obj is None:
            return "Choose a file first."
        if not doc_type:
            return "Select a document type first."

        row = applications.read_application(int(app_id))
        if row and row[2] == "Submitted":
            return "🔒 Application is Submitted. Uploads are locked."

        src_path = getattr(file_obj, "name", None) or str(file_obj)
        filename = os.path.basename(src_path)

        dest_dir = os.path.join(UPLOAD_ROOT, f"app_{int(app_id)}")
        _ensure_dir(dest_dir)

        dest_path = os.path.join(dest_dir, filename)
        shutil.copy(src_path, dest_path)

        applications.add_document(int(app_id), doc_type, filename, dest_path)

        level, _name, _status = applications.read_application(int(app_id))
        progress_text, new_status, _missing = compute_progress_and_status(int(app_id), level)
        if _status != "Submitted":
            applications.update_application_status(int(app_id), new_status)

        return f"✅ Uploaded: {filename}. Progress: {progress_text}. Status: {new_status}"
    except Exception as e:
        return f"❌ Upload failed: {e}"


def delete_one_doc(user_id, app_id, doc_id):
    try:
        if not user_id:
            return "Not logged in."
        if not app_id:
            return "Select an application first."
        if not doc_id:
            return "Select a document first."

        row = applications.read_application(int(app_id))
        if row and row[2] == "Submitted":
            return "🔒 Application is Submitted. Deletions are locked."

        ok = delete_doc_by_id(int(doc_id))
        if not ok:
            return "❌ Not found."

        level, _name, _status = applications.read_application(int(app_id))
        progress_text, new_status, _missing = compute_progress_and_status(int(app_id), level)
        if _status != "Submitted":
            applications.update_application_status(int(app_id), new_status)

        return f"✅ Deleted. Progress: {progress_text}. Status: {new_status}"
    except Exception as e:
        return f"❌ Delete failed: {e}"


def delete_all_docs(user_id, app_id):
    try:
        if not user_id:
            return "Not logged in."
        if not app_id:
            return "Select an application first."

        row = applications.read_application(int(app_id))
        if row and row[2] == "Submitted":
            return "🔒 Application is Submitted. Deletions are locked."

        n = delete_all_docs_for_application(int(app_id))

        level, _name, _status = applications.read_application(int(app_id))
        progress_text, new_status, _missing = compute_progress_and_status(int(app_id), level)
        if _status != "Submitted":
            applications.update_application_status(int(app_id), new_status)

        return f"✅ Deleted {n} document(s). Progress: {progress_text}. Status: {new_status}"
    except Exception as e:
        return f"❌ Delete-all failed: {e}"


def submit_application(user_id, app_id):
    if not user_id:
        return "Not logged in."
    if not app_id:
        return "Select an application first."

    row = applications.read_application(int(app_id))
    if not row:
        return "Application not found."

    level, _name, status = row
    if status == "Submitted":
        return "Already submitted."

    _progress_text, computed_status, missing = compute_progress_and_status(int(app_id), level)
    if computed_status != "Complete":
        return f"❌ Not ready to submit. Missing: {', '.join(missing) if missing else 'unknown'}"

    applications.submit_application(int(app_id))
    return "✅ Application submitted! Uploads and deletions are now locked."


# =========================
# ADMIN (clean layout)
# =========================
def admin_refresh(user_id):
    if not user_id:
        return "Not logged in.", []
    if not auth.is_admin_user(int(user_id)):
        return "Not authorized.", []

    rows = applications.list_all_applications()
    table = [[app_id, uid, lvl, prog, status, ts] for app_id, uid, lvl, prog, status, ts in rows]
    return f"Found {len(rows)} total applications.", table


def admin_set_status(user_id, app_id, new_status, note):
    if not user_id:
        return "Not logged in."
    if not auth.is_admin_user(int(user_id)):
        return "Not authorized."
    if not app_id:
        return "Select an application id."

    app_id = int(app_id)
    applications.update_application_status(app_id, new_status)

    note = (note or "").strip()
    if new_status == "Rejected" and not note:
        return "❌ Please write a reason when rejecting."

    applications.add_decision_note(
        application_id=app_id,
        admin_user_id=int(user_id),
        new_status=new_status,
        note=note,
    )
    return f"✅ Updated application #{app_id} to {new_status}"


# =========================
# PORTAL AI
# =========================
def portal_chat_fn(message, history, user_id_val, app_id_val):
    message = (message or "").strip()
    if not message:
        return "Type a message."
    if not user_id_val:
        return "🔒 Please log in first."

    intent = detect_intent(message)

    if intent == "LIST_APPS":
        apps = list_my_applications(int(user_id_val))
        if not apps:
            return "You don’t have any applications yet."
        return "Your applications:\n" + "\n".join(
            f"- (#{a['app_id']}) [{a['level']}] {a['programme']} — {a['status']}"
            for a in apps
        )

    info = application_summary(int(app_id_val)) if app_id_val else None
    if info and info.get("status") == "Submitted":
        if intent in {"DELETE_ALL_DOCS", "DELETE_DOC_ID"}:
            return "🔒 This application is Submitted. Document deletion is locked."

    if intent == "MISSING_DOCS":
        if not app_id_val:
            return "Select an application first (Application Page dropdown)."
        if not info:
            return "Application not found."
        if not info["missing_types"]:
            return "✅ All required documents are uploaded."
        return "You are missing:\n" + "\n".join(f"- {x}" for x in info["missing_types"])

    if intent == "DELETE_ALL_DOCS":
        if not app_id_val:
            return "Select an application first."
        n = delete_all_docs_for_application(int(app_id_val))
        return f"✅ Deleted {n} document(s) for application #{app_id_val}."

    if intent == "DELETE_DOC_ID":
        m = re.search(r"(#|id\s*)(\d+)", message.lower())
        if not m:
            return "Tell me the document id, e.g. 'delete doc id 12'."
        doc_id = int(m.group(2))
        ok = delete_doc_by_id(doc_id)
        return "✅ Deleted." if ok else "❌ Not found."

    ctx = ""
    if info:
        ctx = (
            f"\nApplication context:\n"
            f"- Application ID: {info['app_id']}\n"
            f"- Level: {info['level']}\n"
            f"- Programme: {info['programme']}\n"
            f"- Status: {info.get('status','')}\n"
            f"- Uploaded: {info['uploaded_types']}\n"
            f"- Missing: {info['missing_types']}\n"
        )
        latest_row = applications.get_latest_decision_row(int(info["app_id"]))
        if latest_row:
            decision_ts, decision_status, decision_note, _admin_id = latest_row
            ctx += f"- Latest decision: {decision_ts} / {decision_status} / {decision_note}\n"

    prompt = (
        "You are a helpful admissions assistant for a student application portal.\n"
        "Use the application context if provided.\n"
        f"{ctx}\nUser: {message}\nAssistant:"
    )
    return ask_llm(prompt)


# =========================
# Logout (global top-right)
# =========================
def do_logout_reset():
    return (
        "✅ Logged out.",
        None,  # user_id_state
        None,  # selected_app_id_state
        gr.update(visible=True),   # public_group
        gr.update(visible=False),  # private_group
        gr.update(visible=False),  # topbar_group
        gr.update(visible=False),  # student_group
        gr.update(visible=False),  # admin_only_group
        "Not loaded.",             # dash_out
        [],                        # apps_table
        gr.update(choices=[], value=None),  # apps_dropdown
        "Select an application from the dropdown.",  # app_summary
        "—", "—", "—",             # app_level/name/status
        gr.update(choices=[], value=None),  # req_doc_type
        "",                        # upload_out
        "No documents loaded.",    # docs_out
        gr.update(choices=[], value=None),  # delete_doc_dropdown
        "",                        # delete_out
        "",                        # student_note
        gr.update(visible=False),  # submit_btn
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        "",                        # admin_note
        "Not loaded.",             # admin_status
        [],                        # admin_table
        "",                        # admin_update_out
        "",                        # whoami_text
    )


# =========================
# UI
# =========================
with gr.Blocks(title="Student Application Portal (Beta)") as demo:
    user_id_state = gr.State(None)
    selected_app_id_state = gr.State(None)

    # Visible when NOT logged in
    public_group = gr.Group(visible=True)

    # Visible when logged in
    private_group = gr.Group(visible=False)

    # Global top bar (visible only when logged in)
    topbar_group = gr.Group(visible=False)
    with topbar_group:
        with gr.Row():
            whoami_text = gr.Markdown("")  # left
            gr.Markdown("")                # spacer
            logout_btn = gr.Button("Logout")  # right

    # ------------------ PUBLIC ------------------
    with public_group:
        with gr.Tabs():
            with gr.Tab("Degrees"):
                gr.Markdown(degrees_markdown())

            with gr.Tab("AI (Public)"):
                gr.Markdown("Ask about programmes and required documents before registering.")
                pub_level = gr.Radio(choices=["Bachelor", "Master"], value="Bachelor", label="Programme Level")
                pub_programme = gr.Dropdown(choices=BACHELOR_PROGRAMMES, label="Programme")
                pub_level.change(update_programmes, inputs=[pub_level], outputs=[pub_programme])

                pub_q = gr.Textbox(label="Your question", lines=2, max_lines=6)
                pub_btn = gr.Button("Ask")
                pub_a = gr.Textbox(label="Answer", lines=8, max_lines=12)
                pub_btn.click(ai_public_answer, inputs=[pub_q, pub_level, pub_programme], outputs=[pub_a])

            with gr.Tab("Account"):
                gr.Markdown("### Register")
                r_name = gr.Textbox(label="Full Name", lines=1, max_lines=1)
                r_email = gr.Textbox(label="Email (register)", lines=1, max_lines=1)
                r_pass = gr.Textbox(label="Password (register)", type="password", lines=1, max_lines=1)
                r_btn = gr.Button("Register")

                gr.Markdown("### Sign In")
                l_email = gr.Textbox(label="Email (login)", lines=1, max_lines=1)
                l_pass = gr.Textbox(label="Password (login)", type="password", lines=1, max_lines=1)
                l_btn = gr.Button("Login")

                auth_out = gr.Textbox(label="Status", interactive=False, lines=2, max_lines=2)

    # ------------------ PRIVATE (container) ------------------
    with private_group:
        # Student-only UI
        student_group = gr.Group(visible=False)
        with student_group:
            with gr.Tabs():
                with gr.Tab("Dashboard"):
                    gr.Markdown("## Apply to a programme")
                    d_level = gr.Radio(choices=["Bachelor", "Master"], value="Bachelor", label="Programme Level")
                    d_programme = gr.Dropdown(choices=BACHELOR_PROGRAMMES, label="Programme")
                    d_level.change(update_programmes, inputs=[d_level], outputs=[d_programme])
                    req_preview = gr.Markdown("Select a programme to see the typical required documents.")
                    d_programme.change(requirements_md, inputs=[d_level, d_programme], outputs=[req_preview])
                    d_level.change(requirements_md, inputs=[d_level, d_programme], outputs=[req_preview])
                    apply_btn = gr.Button("Apply / Create Application")
                    apply_out = gr.Textbox(label="Result", interactive=False, lines=2, max_lines=4)

                    refresh_btn = gr.Button("Refresh applications list")
                    dash_out = gr.Textbox(label="Dashboard Status", interactive=False, lines=1, max_lines=2)

                    apps_table = gr.Dataframe(
                        headers=["App ID", "Level", "Programme", "Status", "Created"],
                        datatype=["number", "str", "str", "str", "str"],
                        interactive=False,
                        row_count=0,
                        column_count=(5, "fixed"),
                    )

                with gr.Tab("Application Page"):
                    gr.Markdown("## Select application")
                    apps_dropdown = gr.Dropdown(choices=[], label="Your Applications")

                    app_summary = gr.Markdown("Select an application from the dropdown.")
                    app_level = gr.Textbox(label="Level", interactive=False)
                    app_name = gr.Textbox(label="Programme", interactive=False)
                    app_status = gr.Textbox(label="Status", interactive=False)

                    student_note = gr.Textbox(
                        label="Admin note / decision reason",
                        interactive=False,
                        lines=3,
                        max_lines=6,
                    )

                    req_doc_type = gr.Dropdown(choices=[], label="Required Document Type")
                    file_obj = gr.File(label="Upload file")
                    upload_btn = gr.Button("Upload Document")
                    upload_out = gr.Textbox(label="Upload Result", interactive=False, lines=1, max_lines=3)

                    docs_out = gr.Textbox(label="Uploaded Documents", lines=10, max_lines=18, interactive=False)

                    gr.Markdown("## Delete uploaded documents")
                    delete_doc_dropdown = gr.Dropdown(choices=[], label="Select document to delete")
                    delete_one_btn = gr.Button("Delete selected document")
                    delete_all_btn = gr.Button("Delete ALL documents for this application")
                    delete_out = gr.Textbox(label="Delete Result", interactive=False, lines=1, max_lines=3)

                    submit_btn = gr.Button("✅ Submit Application", visible=False)

                with gr.Tab("AI Assistant (Portal)"):
                    gr.Markdown("This assistant knows your selected application and can tell you what’s missing.")
                    gr.ChatInterface(
                        fn=portal_chat_fn,
                        additional_inputs=[user_id_state, selected_app_id_state],
                    )

        # Admin-only UI (clean)
        admin_only_group = gr.Group(visible=False)
        with admin_only_group:
            gr.Markdown("## Admin / Reviewer Console")
            with gr.Row():
                admin_refresh_btn = gr.Button("Refresh applications")
                admin_status = gr.Textbox(label="Admin status", interactive=False)

            admin_table = gr.Dataframe(
                headers=["App ID", "User ID", "Level", "Programme", "Status", "Created"],
                interactive=False,
            )

            with gr.Row():
                admin_app_id = gr.Number(label="Application ID", precision=0)
                admin_new_status = gr.Dropdown(
                    choices=["Submitted", "Approved", "Rejected", "In Progress", "Complete"],
                    value="Approved",
                    label="Set status",
                )

            admin_note = gr.Textbox(
                label="Decision note (shown to student; required for Rejected)",
                lines=4,
                max_lines=10,
            )

            admin_update_btn = gr.Button("Apply decision")
            admin_update_out = gr.Textbox(label="Update result", interactive=False)

    # =========================
    # WIRING
    # =========================
    def _after_login(uid: int):
        is_admin = auth.is_admin_user(int(uid))
        email = auth.get_user_email(int(uid))
        who = f"**Logged in as:** `{email}`" + (" (admin)" if is_admin else "")
        return (
            gr.update(visible=False),  # public
            gr.update(visible=True),   # private
            gr.update(visible=True),   # topbar
            gr.update(visible=(not is_admin)),  # student_group
            gr.update(visible=is_admin),        # admin_only_group
            who,
        )

    def on_register(name, email, pw):
        status, uid = do_register(name, email, pw)
        if uid:
            a = _after_login(uid)
            return (status, uid) + a
        return (
            status, None,
            gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False),
            "",
        )

    def on_login(email, pw):
        status, uid = do_login(email, pw)
        if uid:
            a = _after_login(uid)
            return (status, uid) + a
        return (
            status, None,
            gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False),
            "",
        )

    # Register/Login actions
    r_btn.click(
        on_register,
        [r_name, r_email, r_pass],
        [auth_out, user_id_state, public_group, private_group, topbar_group, student_group, admin_only_group, whoami_text]
    )
    l_btn.click(
        on_login,
        [l_email, l_pass],
        [auth_out, user_id_state, public_group, private_group, topbar_group, student_group, admin_only_group, whoami_text]
    )

    # Student dashboard refresh after login/register
    def post_login_refresh(uid):
        msg, table, dd = refresh_apps(uid)
        return msg, table, dd

    r_btn.click(post_login_refresh, [user_id_state], [dash_out, apps_table, apps_dropdown])
    l_btn.click(post_login_refresh, [user_id_state], [dash_out, apps_table, apps_dropdown])

    # Student apply + refresh list
    apply_btn.click(apply_create, [user_id_state, d_level, d_programme], [apply_out, selected_app_id_state])
    apply_btn.click(refresh_apps, [user_id_state], [dash_out, apps_table, apps_dropdown])
    apply_btn.click(lambda x: x, [selected_app_id_state], [apps_dropdown])

    refresh_btn.click(refresh_apps, [user_id_state], [dash_out, apps_table, apps_dropdown])

    # Shared outputs for load_application (prevents mismatched ordering bugs)
    LOAD_APP_OUTPUTS = [
        app_summary, app_level, app_name, app_status,
        req_doc_type, upload_out, docs_out, delete_doc_dropdown, delete_out,
        student_note,
        submit_btn, upload_btn, delete_one_btn, delete_all_btn, file_obj, req_doc_type
    ]

    # Select app
    apps_dropdown.change(lambda x: x, [apps_dropdown], [selected_app_id_state])
    apps_dropdown.change(load_application, [user_id_state, apps_dropdown], LOAD_APP_OUTPUTS)

    # Upload -> refresh docs + reload
    upload_btn.click(upload_doc, [user_id_state, apps_dropdown, req_doc_type, file_obj], [upload_out])
    upload_btn.click(docs_text_and_delete_choices, [user_id_state, apps_dropdown], [docs_out, delete_doc_dropdown])
    upload_btn.click(load_application, [user_id_state, apps_dropdown], LOAD_APP_OUTPUTS)

    # Delete selected -> refresh docs + reload
    delete_one_btn.click(delete_one_doc, [user_id_state, apps_dropdown, delete_doc_dropdown], [delete_out])
    delete_one_btn.click(docs_text_and_delete_choices, [user_id_state, apps_dropdown], [docs_out, delete_doc_dropdown])
    delete_one_btn.click(load_application, [user_id_state, apps_dropdown], LOAD_APP_OUTPUTS)

    # Delete all -> refresh docs + reload
    delete_all_btn.click(delete_all_docs, [user_id_state, apps_dropdown], [delete_out])
    delete_all_btn.click(docs_text_and_delete_choices, [user_id_state, apps_dropdown], [docs_out, delete_doc_dropdown])
    delete_all_btn.click(load_application, [user_id_state, apps_dropdown], LOAD_APP_OUTPUTS)

    # Submit -> reload + refresh dashboard list
    submit_btn.click(submit_application, [user_id_state, apps_dropdown], [upload_out])
    submit_btn.click(load_application, [user_id_state, apps_dropdown], LOAD_APP_OUTPUTS)
    submit_btn.click(refresh_apps, [user_id_state], [dash_out, apps_table, apps_dropdown])

    # Admin
    admin_refresh_btn.click(admin_refresh, [user_id_state], [admin_status, admin_table])
    admin_update_btn.click(admin_set_status, [user_id_state, admin_app_id, admin_new_status, admin_note], [admin_update_out])
    admin_update_btn.click(admin_refresh, [user_id_state], [admin_status, admin_table])

    # Global logout (top-right)
    logout_btn.click(
        do_logout_reset,
        [],
        [
            auth_out, user_id_state, selected_app_id_state,
            public_group, private_group, topbar_group, student_group, admin_only_group,
            dash_out, apps_table, apps_dropdown,
            app_summary, app_level, app_name, app_status,
            req_doc_type, upload_out, docs_out,
            delete_doc_dropdown, delete_out,
            student_note,
            submit_btn, upload_btn, delete_one_btn, delete_all_btn, file_obj, req_doc_type,
            admin_note, admin_status, admin_table, admin_update_out,
            whoami_text,
        ],
    )

import os

port = int(os.environ.get("PORT", "7860"))
demo.launch(server_name="0.0.0.0", server_port=port)

