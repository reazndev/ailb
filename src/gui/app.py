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
    c1, c2, c3 = st.columns(3)
    with c1:
        provider_key_map = {
            "OpenAI": "openai",
            "Anthropic (Claude)": "anthropic_claude",
            "Google (Gemini)": "google_gemini",
            "DeepSeek": "deepseek",
            "OpenRouter": "openrouter"
        }
        # Invert map for display
        display_providers = list(provider_key_map.keys())
        selected_display_provider = st.selectbox("Provider", display_providers)
        provider_key = provider_key_map[selected_display_provider]
        
        # Determine actual provider string for Agent class (needs normalization)
        agent_provider_arg = "openai"
        if provider_key == "anthropic_claude": agent_provider_arg = "anthropic"
        elif provider_key == "google_gemini": agent_provider_arg = "gemini"
        elif provider_key == "deepseek": agent_provider_arg = "deepseek"
        elif provider_key == "openrouter": agent_provider_arg = "openrouter"

    with c2:
        # Get models from our static detailed data first
        static_models = MODEL_DATA.get(provider_key, {})
        model_options = list(static_models.keys())
        
        # Also try to fetch dynamic ones if needed, or just stick to the curated list
        # For now, we append "Manual Entry"
        model_options.append("Manual Entry...")
        
        # Format for display: "Name (Context) - $Price"
        def format_func(option):
            if option == "Manual Entry...": return option
            m = static_models[option]
            return f"{m['name']} ({m['context']}) - ${m['input_price']}/1M in"
            
        selected_option = st.selectbox("Model", model_options, format_func=format_func)
        
        if selected_option == "Manual Entry...":
            model = st.text_input("Enter Model ID", value="gpt-4o")
        else:
            model = selected_option
            # Show notes
            m_data = static_models[selected_option]
            st.caption(f"📝 {m_data.get('notes', '')}")
            st.caption(f"💰 In: ${m_data['input_price']} | Out: ${m_data['output_price']} (per 1M)")

    with c3:
        cost_limit = st.number_input("Cost Limit ($)", value=1.0, step=0.1)
        st.session_state['cost_limit'] = cost_limit

    # Project Selection
    hz_list = scan_directory("data")
    if not hz_list:
        st.warning("No projects found in `data/`. Go to Project Manager to create one.")
        return

    hz_names = [hz.name for hz in hz_list]
    selected_hz = st.selectbox("Select Project (HZ)", hz_names)

    # Main Action
    if st.button("Start Agent", disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.session_state.logs = []
        st.session_state.cost = 0.0
        st.session_state.tokens = {"input": 0, "output": 0}
        
        # Prepare Data
        current_hz = next(hz for hz in hz_list if hz.name == selected_hz)
        
        # UI Placeholders
        log_container = st.container()
        status_text = st.empty()
        
        # Define Callbacks
        def log_callback(msg):
            st.session_state.logs.append(msg)
            # We can't easily force-redraw loop inside a callback in Streamlit synchronous flow without `st.rerun` or tricky constructs.
            # But writing to a placeholder works usually.
            status_text.text(f"Last Log: {msg}")
            
        def update_callback(data):
            st.session_state.cost = data["total_cost"]
            st.session_state.tokens = data["tokens"]
            
        try:
            agent = Agent(provider=agent_provider_arg, model=model, cost_limit=cost_limit)
            agent.on_log = log_callback
            agent.on_update = update_callback
            
            # Load Content
            with st.spinner("Loading files..."):
                input_texts = {}
                for f in current_hz.input_files:
                    c = load_file_content(f)
                    if c: input_texts[f] = c
                
                assignment_text = ""
                for f in current_hz.assignment_files:
                    c = load_file_content(f)
                    if c: assignment_text += f"\n\n{c}"
            
            # Run
            with st.spinner("Agent is working... (Check sidebar for live costs)"):
                result = agent.run(selected_hz, assignment_text, input_texts)
            
            # Save
            out_path = os.path.join("output", selected_hz)
            os.makedirs(out_path, exist_ok=True)
            with open(os.path.join(out_path, "solution.md"), "w") as f:
                f.write(result)
            
            st.success(f"Finished! Saved to output/{selected_hz}/solution.md")
            st.markdown("### Generated Solution Preview")
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
                st.success(f"Created {new_name}")
                # Wait a tiny bit to let the user see the success message before rerun
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
            c1, c2 = st.columns(2)
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
                    for f in up_in:
                        dest = os.path.join(hz.path, "Input", f.name)
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
                    for f in up_ass:
                        dest = os.path.join(hz.path, "Assignments", f.name)
                        with open(dest, "wb") as w:
                            w.write(f.getvalue())
                    st.success("Uploaded Assignment Files!")
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
