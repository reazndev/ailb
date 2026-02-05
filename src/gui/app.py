import streamlit as st
import os
import shutil
import time
from src.ingestion.scanner import scan_directory
from src.ingestion.loader import load_file_content
from src.agent.core import Agent
from src.utils.pricing_data import MODEL_DATA, PRICING_REGISTRY
from src.utils.models import get_available_models

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

# --- SIDEBAR ---
st.sidebar.title("🎓 AI Student")
page = st.sidebar.radio("Navigation", ["Dashboard", "Project Manager", "Settings"])

st.sidebar.markdown("---")
st.sidebar.markdown("### Cost Tracker")
cost_col1, cost_col2 = st.sidebar.columns(2)
cost_col1.metric("Cost", f"${st.session_state.cost:.4f}")
cost_col2.metric("Limit", f"${st.session_state.get('cost_limit', 1.0):.2f}")

st.sidebar.text(f"In Tokens: {st.session_state.tokens['input']}")
st.sidebar.text(f"Out Tokens: {st.session_state.tokens['output']}")

# --- PAGES ---

def page_dashboard():
    st.title("🚀 Dashboard")
    
    # Provider Selection
    c1, c2, c3, c4 = st.columns(4)
    with c1:
...
    with c3:
        cost_limit = st.number_input("Cost Limit ($)", value=1.0, step=0.1)
        st.session_state['cost_limit'] = cost_limit
        
    with c4:
        max_parallel = st.slider("Parallel Agents", min_value=1, max_value=10, value=5)

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
        # Get basenames for display
        ass_map = {os.path.basename(f): f for f in current_hz.assignment_files}
        all_ass_names = list(ass_map.keys())
        
        # Initialize state for multiselect if not present or if project changed
        # We use a composite key to reset selection when project changes
        ms_key = f"ms_{selected_hz_name}"
        if ms_key not in st.session_state:
             st.session_state[ms_key] = all_ass_names
             
        # Select All / Deselect All Handlers
        def select_all():
            st.session_state[ms_key] = all_ass_names
        
        def deselect_all():
            st.session_state[ms_key] = []
            
        # Buttons
        b1, b2 = st.columns([0.3, 0.7])
        b1.button("Select All", on_click=select_all, key=f"btn_all_{selected_hz_name}")
        b2.button("Deselect All", on_click=deselect_all, key=f"btn_none_{selected_hz_name}")

        # Multiselect
        selected_ass_names = st.multiselect(
            "Select Assignments to Solve", 
            options=all_ass_names,
            key=ms_key
        )
        
        selected_ass_paths = [ass_map[name] for name in selected_ass_names]

    with ac2:
        custom_prompt = st.text_area("Custom Instructions (Optional)", placeholder="e.g., Focus heavily on Python list comprehensions...", height=100)

    # Main Action
    if st.button("Start Agent", disabled=st.session_state.is_running):
        if not selected_ass_paths:
            st.error("Please select at least one assignment.")
        else:
            st.session_state.is_running = True
            st.session_state.logs = []
            st.session_state.cost = 0.0
            st.session_state.tokens = {"input": 0, "output": 0}
            
            # UI Placeholders
            log_container = st.container()
            status_text = st.empty()
            
            # Progress Area
            st.markdown("### 📊 Progress")
            progress_bar = st.progress(0)
            with st.expander("📝 Task List", expanded=True):
                task_list_ph = st.empty()
                task_list_ph.info("Waiting for plan...")

            # Preview Area
            st.markdown("---")
            st.markdown("### 👁️ Live Preview")
            p1, p2, p3 = st.columns(3)
            with p1: 
                st.subheader("Current Task (QA Criteria)")
                req_ph = st.empty()
                req_ph.info("Waiting for agent to start task...")
            with p2:
                st.subheader("Generated Draft")
                draft_ph = st.empty()
                draft_ph.info("Waiting for draft...")
            with p3:
                st.subheader("QA Feedback")
                qa_ph = st.empty()
                qa_ph.info("Waiting for QA review...")
            
            def log_callback(msg):
                st.session_state.logs.append(msg)
                status_text.text(f"Last Log: {msg}")
                
            def update_callback(data):
                st.session_state.cost = data["total_cost"]
                st.session_state.tokens = data["tokens"]
                
            # State to hold current tasks for this assignment
            current_tasks_ref = {"tasks": []}

            def plan_callback(tasks):
                current_tasks_ref["tasks"] = tasks
                # Render initial list
                md_list = "\n".join([f"- [ ] {t}" for t in tasks])
                task_list_ph.markdown(md_list)
                progress_bar.progress(0)

            def section_callback(task, reqs, i, total):
                # Update Progress Bar
                # i is 0-indexed, so 0/total is start. (i+1)/total is end of task? 
                # Let's say we are working on task i.
                p = float(i) / float(total)
                progress_bar.progress(p)
                
                # Update Task List
                # Mark 0 to i-1 as [x], i as [x] (in progress), others [ ]
                # Or maybe style current differently? Markdown doesn't support bolding checkbox line easily.
                # We'll mark current as [x] assuming "working on it".
                tasks = current_tasks_ref["tasks"]
                md_lines = []
                for idx, t in enumerate(tasks):
                    if idx < i:
                        md_lines.append(f"- [x] ~{t}~") # Strike through done
                    elif idx == i:
                        md_lines.append(f"- [ ] **{t}** (Current)")
                    else:
                        md_lines.append(f"- [ ] {t}")
                task_list_ph.markdown("\n".join(md_lines))

                req_ph.markdown(f"#### Task: {task}\n\n**Assignment / QA Criteria:**\n\n> {reqs[:800]}...")
                
            def draft_callback(text):
                draft_ph.markdown(f"```markdown\n{text[:1500]}...\n```\n*(Draft truncated for preview)*")
                
            def qa_callback(text):
                if "PASS" in text:
                    qa_ph.success("✅ QA Passed!")
                else:
                    qa_ph.warning(f"**Professor's Feedback:**\n\n{text}")

            try:
                agent = Agent(provider=agent_provider_arg, model=model, cost_limit=cost_limit, max_parallel=max_parallel)
                agent.on_log = log_callback
                agent.on_update = update_callback
                agent.on_section_start = section_callback
                agent.on_draft = draft_callback
                agent.on_qa_feedback = qa_callback
                agent.on_plan_generated = plan_callback
                
                # Load Inputs + Solutions as Context
                with st.spinner("Loading context files..."):
                    input_texts = {}
                    # Load Inputs
                    for f in current_hz.input_files:
                        c = load_file_content(f)
                        if c: input_texts[f] = c
                    
                    # Load Solutions (as reference material)
                    for f in current_hz.solutions_files:
                         c = load_file_content(f)
                         if c: input_texts[f"SOLUTION_REF_{os.path.basename(f)}"] = c
                
                # Run Agent
                with st.spinner("Agent is working..."):
                    # We now pass the list of assignment paths and the custom prompt
                    result = agent.run(
                        hz_name=selected_hz_name, 
                        assignment_paths=selected_ass_paths, 
                        input_texts=input_texts,
                        custom_prompt=custom_prompt
                    )
                
                st.success(f"Finished! Processed {len(selected_ass_paths)} assignments.")
                st.markdown("### Agent Report")
                st.markdown(result)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                
            finally:
                st.session_state.is_running = False

    # Log Viewer
    with st.expander("Execution Logs", expanded=True):
        for log in st.session_state.logs:
            st.text(log)

def page_project_manager():
    st.title("📂 Project Manager")
    
    # Create New
    with st.form("new_hz"):
        new_name = st.text_input("New Project Name (e.g., HZ_NewTopic)")
        submitted = st.form_submit_button("Create Project")
        
    if submitted:
        if new_name:
            path = os.path.join("data", new_name)
            try:
                os.makedirs(os.path.join(path, "Input"), exist_ok=True)
                os.makedirs(os.path.join(path, "Assignments"), exist_ok=True)
                os.makedirs(os.path.join(path, "Solutions"), exist_ok=True)
                st.success(f"Created {new_name}")
                time.sleep(0.5) 
                st.rerun()
            except Exception as e:
                st.error(f"Error creating project: {e}")
        else:
            st.error("Please enter a name.")

    st.markdown("---")
    
    # File Browser
    hz_list = scan_directory("data")
    for hz in hz_list:
        with st.expander(hz.name):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("Input Files")
                for f in hz.input_files:
                    st.text(f"📄 {os.path.basename(f)}")
                
                # Upload Input
                up_in = st.file_uploader(
                    f"Add to {hz.name}/Input", 
                    key=f"in_{hz.name}", 
                    accept_multiple_files=True,
                    type=["pdf", "docx", "pptx", "txt", "md"]
                )
                if up_in:
                    input_dir = os.path.join(hz.path, "Input")
                    os.makedirs(input_dir, exist_ok=True)
                    for f in up_in:
                        dest = os.path.join(input_dir, f.name)
                        with open(dest, "wb") as w:
                            w.write(f.getvalue())
                    st.success("Uploaded Input Files!")
                    time.sleep(0.5)
                    st.rerun()

            with c2:
                st.subheader("Assignments")
                for f in hz.assignment_files:
                    st.text(f"📝 {os.path.basename(f)}")
                    
                # Upload Assignment
                up_ass = st.file_uploader(
                    f"Add to {hz.name}/Assignments", 
                    key=f"ass_{hz.name}", 
                    accept_multiple_files=True,
                    type=["pdf", "docx", "txt", "md"]
                )
                if up_ass:
                    ass_dir = os.path.join(hz.path, "Assignments")
                    os.makedirs(ass_dir, exist_ok=True)
                    for f in up_ass:
                        dest = os.path.join(ass_dir, f.name)
                        with open(dest, "wb") as w:
                            w.write(f.getvalue())
                    st.success("Uploaded Assignment Files!")
                    time.sleep(0.5)
                    st.rerun()
            
            with c3:
                st.subheader("Reference Solutions")
                for f in hz.solutions_files:
                    st.text(f"💡 {os.path.basename(f)}")
                
                # Upload Solutions
                up_sol = st.file_uploader(
                    f"Add to {hz.name}/Solutions", 
                    key=f"sol_{hz.name}", 
                    accept_multiple_files=True,
                    type=["pdf", "docx", "txt", "md"]
                )
                if up_sol:
                    sol_dir = os.path.join(hz.path, "Solutions")
                    os.makedirs(sol_dir, exist_ok=True)
                    for f in up_sol:
                        dest = os.path.join(sol_dir, f.name)
                        with open(dest, "wb") as w:
                            w.write(f.getvalue())
                    st.success("Uploaded Solution!")
                    time.sleep(0.5)
                    st.rerun()

def page_settings():
    st.title("⚙️ Settings")
    st.markdown("Manage your `.env` file from here.")
    
    env_path = ".env"
    if not os.path.exists(env_path):
        st.warning(".env file not found!")
    else:
        with open(env_path, "r") as f:
            current_env = f.read()
            
        new_env = st.text_area("Edit .env content", value=current_env, height=300)
        
        if st.button("Save .env"):
            with open(env_path, "w") as f:
                f.write(new_env)
            st.success("Saved! Reload the app to apply changes.")
            
    st.markdown("### Pricing Info (Per 1M Tokens)")
    st.json(MODEL_DATA)

# --- ROUTER ---
if page == "Dashboard":
    page_dashboard()
elif page == "Project Manager":
    page_project_manager()
elif page == "Settings":
    page_settings()
