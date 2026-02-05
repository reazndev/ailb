import streamlit as st
import os
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from src.ingestion.scanner import scan_directory
from src.ingestion.loader import load_file_content
from src.agent.core import Agent
from src.utils.pricing_data import MODEL_DATA, PRICING_REGISTRY
from src.utils.models import get_available_models

# Try to import Streamlit context helpers for thread safety
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    try:
        from streamlit.scriptrunner import add_script_run_ctx, get_script_run_ctx
    except ImportError:
        add_script_run_ctx = None
        get_script_run_ctx = None

st.set_page_config(page_title="AI Student Agent", layout="wide", page_icon="🎓")

# --- STATE MANAGEMENT ---
if "logs" not in st.session_state:
    st.session_state.logs = []
if "cost" not in st.session_state:
    st.session_state.cost = 0.0
if "tokens" not in st.session_state:
    st.session_state.tokens = {"input": 0, "output": 0}
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "agent_future" not in st.session_state:
    st.session_state.agent_future = None
if "executor" not in st.session_state:
    st.session_state.executor = ThreadPoolExecutor(max_workers=1)
if "assignments_tasks" not in st.session_state:
    st.session_state.assignments_tasks = {} # filename -> {"tasks": [], "statuses": {}, "logs": [], "draft": "", "reqs": "", "qa": "", "status_msg": ""}
if "agent_result" not in st.session_state:
    st.session_state.agent_result = ""

# --- SIDEBAR ---
# ... (rest of sidebar code)

# --- CALLBACKS ---
def log_callback(msg, ass_name=None):
    if ass_name and ass_name in st.session_state.assignments_tasks:
        st.session_state.assignments_tasks[ass_name]["logs"].append(msg)
        # Update status message if it's short and looks like a status
        if len(msg) < 40 and not msg.startswith("Loaded"):
            st.session_state.assignments_tasks[ass_name]["status_msg"] = msg
    else:
        st.session_state.logs.append(msg)
    
def update_callback(data):
    st.session_state.cost = data["total_cost"]
    st.session_state.tokens = data["tokens"]

def plan_callback(ass_name, tasks):
    st.session_state.assignments_tasks[ass_name] = {
        "tasks": tasks,
        "statuses": {i: "pending" for i in range(len(tasks))},
        "logs": [],
        "draft": "",
        "reqs": "",
        "qa": "",
        "status_msg": "Plan generated"
    }
    
def section_callback(ass_name, task, reqs, i, total):
    if ass_name in st.session_state.assignments_tasks:
        st.session_state.assignments_tasks[ass_name]["statuses"][i] = "running"
        st.session_state.assignments_tasks[ass_name]["reqs"] = reqs
        st.session_state.assignments_tasks[ass_name]["status_msg"] = f"Generating task {i+1}..."
    
def draft_callback(ass_name, text):
    if ass_name in st.session_state.assignments_tasks:
        st.session_state.assignments_tasks[ass_name]["draft"] = text
        st.session_state.assignments_tasks[ass_name]["status_msg"] = "Reviewing..."
    
def qa_callback(ass_name, text):
    if ass_name in st.session_state.assignments_tasks:
        st.session_state.assignments_tasks[ass_name]["qa"] = text
        if "PASS" in text:
            st.session_state.assignments_tasks[ass_name]["status_msg"] = "QA Passed ✅"
        else:
            st.session_state.assignments_tasks[ass_name]["status_msg"] = "QA Improvements..."

def task_finished_callback(ass_name, i, text):
    if ass_name in st.session_state.assignments_tasks:
        st.session_state.assignments_tasks[ass_name]["statuses"][i] = "done"
        st.session_state.assignments_tasks[ass_name]["status_msg"] = f"Task {i+1} complete"

def find_file_globally(filename, hz_list):
    """Returns a list of HZ names where the filename exists."""
    found_in = []
    for hz in hz_list:
        all_files = hz.input_files + hz.assignment_files + hz.solutions_files
        if any(os.path.basename(f) == filename for f in all_files):
            found_in.append(hz.name)
    return found_in

def render_file_list_with_delete(file_list):
    """Renders a list of files with a compact delete icon for each."""
    for f in file_list:
        fname = os.path.basename(f)
        fc1, fc2 = st.columns([0.9, 0.1])
        fc1.markdown(f":material/description: {fname}")
        if fc2.button(label="", icon=":material/delete:", key=f"del_{f}", help=f"Delete {fname}"):
            try:
                os.remove(f)
                st.success(f"Deleted {fname}")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

def handle_upload(hz_name, category, uploaded_files, hz_list):
    if not uploaded_files: return
    duplicates = {}
    for f in uploaded_files:
        existing_hzs = find_file_globally(f.name, hz_list)
        if existing_hzs: duplicates[f.name] = existing_hzs
    if duplicates:
        st.warning("⚠️ Some files already exist in other projects:")
        for fname, hzs in duplicates.items(): st.write(f"- **{fname}** is already in: {', '.join(hzs)}")
        if st.button(f"Proceed with upload to {hz_name}/{category}?", key=f"conf_{hz_name}_{category}"):
            save_files(hz_name, category, uploaded_files)
    else:
        if st.button(f"Save {len(uploaded_files)} files to {hz_name}/{category}", key=f"save_{hz_name}_{category}"):
            save_files(hz_name, category, uploaded_files)

def save_files(hz_name, category, uploaded_files):
    target_dir = os.path.join("data", hz_name, category)
    os.makedirs(target_dir, exist_ok=True)
    for f in uploaded_files:
        dest = os.path.join(target_dir, f.name)
        with open(dest, "wb") as w: w.write(f.getvalue())
    st.success(f"Uploaded to {category}!")
    time.sleep(0.5)
    st.rerun()

# --- PAGES ---

def page_dashboard():
    st.title("🚀 Dashboard")
    
    # Provider Selection
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        provider_key_map = {"OpenAI": "openai", "Anthropic (Claude)": "anthropic_claude", "Google (Gemini)": "google_gemini", "DeepSeek": "deepseek", "OpenRouter": "openrouter"}
        selected_display_provider = st.selectbox("Provider", list(provider_key_map.keys()))
        provider_key = provider_key_map[selected_display_provider]
        agent_provider_arg = {"anthropic_claude": "anthropic", "google_gemini": "gemini", "deepseek": "deepseek", "openrouter": "openrouter"}.get(provider_key, "openai")

    with c2:
        static_models = MODEL_DATA.get(provider_key, {})
        model_options = list(static_models.keys()) + ["Manual Entry..."]
        def format_func(option):
            if option == "Manual Entry...": return option
            m = static_models[option]
            return f"{m['name']} ({m['context']}) - ${m['input_price']}/1M in"
        selected_option = st.selectbox("Model", model_options, format_func=format_func)
        if selected_option == "Manual Entry...": model = st.text_input("Enter Model ID", value="gpt-4o")
        else:
            model = selected_option
            m_data = static_models[selected_option]
            st.caption(f"📝 {m_data.get('notes', '')}")
            st.caption(f"💰 In: ${m_data['input_price']} | Out: ${m_data['output_price']} (per 1M)")

    with c3:
        cost_limit = st.number_input("Cost Limit ($)", value=1.0, step=0.1)
        st.session_state['cost_limit'] = cost_limit
        
    with c4:
        max_parallel = st.slider("Max Assignments", min_value=1, max_value=10, value=5)
        max_subtasks = st.slider("Max Subtasks", min_value=1, max_value=10, value=3)
        
    with c5:
        skip_qa = st.checkbox("Skip QA")
        length_profile = st.selectbox("Length", ["Short", "Normal", "Long"], index=2)
        if not skip_qa:
            max_qa_retries = st.number_input("Max QA Retries", min_value=1, max_value=10, value=1)
            min_qa_score = st.number_input("Min Passing Score", min_value=1.0, max_value=10.0, value=9.0, step=0.5)
        else:
            max_qa_retries = 0
            min_qa_score = 9.0

    # Project Selection
    hz_list = scan_directory("data")
    if not hz_list:
        st.warning("No projects found in `data/`. Go to Project Manager to create one.")
        return
    hz_names = [hz.name for hz in hz_list]
    selected_hz_name = st.selectbox("Select Project (HZ)", hz_names)
    current_hz = next(hz for hz in hz_list if hz.name == selected_hz_name)

    # Assignment Selection & Custom Prompt
    st.markdown("### Configuration")
    ac1, ac2 = st.columns(2)
    with ac1:
        ass_map = {os.path.basename(f): f for f in current_hz.assignment_files}
        all_ass_names = list(ass_map.keys())
        ms_key = f"ms_{selected_hz_name}"
        if ms_key not in st.session_state: st.session_state[ms_key] = all_ass_names
        def select_all(): st.session_state[ms_key] = all_ass_names
        def deselect_all(): st.session_state[ms_key] = []
        b1, b2 = st.columns([0.3, 0.7])
        b1.button("Select All", on_click=select_all, key=f"btn_all_{selected_hz_name}")
        b2.button("Deselect All", on_click=deselect_all, key=f"btn_none_{selected_hz_name}")
        selected_ass_names = st.multiselect("Select Assignments to Solve", options=all_ass_names, key=ms_key)
        selected_ass_paths = [ass_map[name] for name in selected_ass_names]
    with ac2:
        custom_prompt = st.text_area("Custom Instructions (Optional)", placeholder="e.g., Focus heavily on Python list comprehensions...", height=100)

    # --- RUNNING STATE MONITORING ---
    if st.session_state.is_running:
        if st.session_state.agent_future.done():
            st.session_state.is_running = False
            try: st.session_state.agent_result = st.session_state.agent_future.result()
            except Exception as e: st.error(f"Agent failed: {e}")
            st.rerun()
        else:
            st.info("Agent is working...")
            if st.button("Force Continue / Skip Step"):
                with open(".skip_signal", "w") as f: f.write("skip")
                st.warning("Signal sent. Waiting for agent...")

            st.markdown("### 📊 Progress & Process")
            if not st.session_state.assignments_tasks:
                st.info("Waiting for plans...")
            else:
                for ass_name, data in st.session_state.assignments_tasks.items():
                    tasks, statuses, logs, draft, reqs, qa = data["tasks"], data["statuses"], data["logs"], data["draft"], data["reqs"], data["qa"]
                    total = len(tasks) if tasks else 1
                    done_count = sum(1 for s in statuses.values() if s == "done")
                    progress_val = min(1.0, max(0.0, done_count / total))
                    
                    with st.expander(f"📁 {ass_name} ({int(progress_val*100)}%)", expanded=True):
                        st.progress(progress_val)
                        tabs = st.tabs(["📝 Task List", "📜 Logs", "👁️ Live Preview"])
                        with tabs[0]:
                            task_html = ""
                            for idx, t in enumerate(tasks):
                                status = statuses.get(idx, "pending")
                                if status == "done": style, icon = "color: gray; text-decoration: line-through;", "✅"
                                elif status == "running":
                                    style = "background-color: #1E90FF; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold;"
                                    icon = "⚙️"
                                else: style, icon = "", "▫️"
                                task_html += f"<div style='margin-bottom: 5px; {style}'>{icon} {t}</div>"
                            st.markdown(task_html, unsafe_allow_html=True)
                        with tabs[1]:
                            for l in logs: st.text(l)
                        with tabs[2]:
                            p1, p2, p3 = st.columns(3)
                            with p1:
                                st.markdown("**Requirements**")
                                if reqs: st.markdown(f"> {reqs[:2000]}...")
                                else: st.info("Waiting...")
                            with p2:
                                st.markdown("**Generated Draft**")
                                if draft: st.markdown(f"```markdown\n{draft[:5000]}...\n```")
                                else: st.info("Waiting...")
                            with p3:
                                st.markdown("**QA Feedback**")
                                if qa:
                                    if "PASS" in qa: st.success("✅ QA Passed!")
                                    else: st.warning(f"{qa}")
                                else: st.info("Waiting...")
            time.sleep(0.5)
            st.rerun()

    if st.session_state.agent_result:
        st.success("All Assignments Finished!")
        with st.expander("🎓 Final Combined Report", expanded=False):
            st.markdown(st.session_state.agent_result)

    st.markdown("---")
    if st.button("Start Agent", disabled=st.session_state.is_running):
        if not selected_ass_paths: st.error("Please select at least one assignment.")
        else:
            st.session_state.is_running, st.session_state.logs, st.session_state.cost, st.session_state.tokens, st.session_state.assignments_tasks, st.session_state.agent_result = True, [], 0.0, {"input": 0, "output": 0}, {}, ""
            try:
                agent = Agent(provider=agent_provider_arg, model=model, cost_limit=cost_limit, max_parallel=max_parallel, max_subtasks=max_subtasks, skip_qa=skip_qa, max_qa_retries=max_qa_retries, min_qa_score=min_qa_score, length_profile=length_profile)
                agent.on_log, agent.on_update, agent.on_section_start, agent.on_draft, agent.on_qa_feedback, agent.on_plan_generated, agent.on_task_finished = log_callback, update_callback, section_callback, draft_callback, qa_callback, plan_callback, task_finished_callback
                with st.spinner("Loading context files..."):
                    input_texts = {}
                    for f in current_hz.input_files:
                        c = load_file_content(f)
                        if c: input_texts[f] = c
                    for f in current_hz.solutions_files:
                         c = load_file_content(f)
                         if c: input_texts[f"SOLUTION_REF_{os.path.basename(f)}"] = c
                ctx = get_script_run_ctx() if get_script_run_ctx else None
                def run_agent_with_context(*args, **kwargs):
                    if add_script_run_ctx and ctx: add_script_run_ctx(threading.current_thread(), ctx)
                    return agent.run(*args, **kwargs)
                st.session_state.agent_future = st.session_state.executor.submit(run_agent_with_context, hz_name=selected_hz_name, assignment_paths=selected_ass_paths, input_texts=input_texts, custom_prompt=custom_prompt)
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.session_state.is_running = False

def page_project_manager():
    st.title("📂 Project Manager")
    with st.form("new_hz"):
        new_name = st.text_input("New Project Name (e.g., HZ_NewTopic)")
        if st.form_submit_button("Create Project"):
            if new_name:
                path = os.path.join("data", new_name)
                try:
                    for d in ["Input", "Assignments", "Solutions"]: os.makedirs(os.path.join(path, d), exist_ok=True)
                    st.success(f"Created {new_name}"); time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else: st.error("Please enter a name.")
    st.markdown("---")
    hz_list = scan_directory("data")
    for hz in hz_list:
        with st.expander(hz.name):
            c1, c2, c3 = st.columns(3)
            with c1: st.subheader("Input Files"); render_file_list_with_delete(hz.input_files); up_in = st.file_uploader(f"Add to {hz.name}/Input", key=f"in_{hz.name}", accept_multiple_files=True, type=["pdf", "docx", "pptx", "txt", "md"]); handle_upload(hz.name, "Input", up_in, hz_list)
            with c2: st.subheader("Assignments"); render_file_list_with_delete(hz.assignment_files); up_ass = st.file_uploader(f"Add to {hz.name}/Assignments", key=f"ass_{hz.name}", accept_multiple_files=True, type=["pdf", "docx", "txt", "md"]); handle_upload(hz.name, "Assignments", up_ass, hz_list)
            with c3: st.subheader("Solutions"); render_file_list_with_delete(hz.solutions_files); up_sol = st.file_uploader(f"Add to {hz.name}/Solutions", key=f"sol_{hz.name}", accept_multiple_files=True, type=["pdf", "docx", "txt", "md"]); handle_upload(hz.name, "Solutions", up_sol, hz_list)

def page_settings():
    st.title("⚙️ Settings")
    env_path = ".env"
    if not os.path.exists(env_path): st.warning(".env not found!")
    else:
        with open(env_path, "r") as f: current_env = f.read()
        new_env = st.text_area("Edit .env content", value=current_env, height=300)
        if st.button("Save .env"):
            with open(env_path, "w") as f: f.write(new_env)
            st.success("Saved! Reload the app.")
    st.markdown("### Pricing Info"); st.json(MODEL_DATA)

if page == "Dashboard": page_dashboard()
elif page == "Project Manager": page_project_manager()
elif page == "Settings": page_settings()