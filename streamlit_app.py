import streamlit as st
import uuid

from langchain_core.messages import HumanMessage
from app.runtime.llm_mvp import build_mvp_graph

st.set_page_config(page_title="Tribe Leader", layout="centered")
st.title("Tribe Leader")

# ---- Session wiring ----
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"tribe:{uuid.uuid4().hex}"

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---- Reset conversation ----
def reset_conversation():
    st.session_state.thread_id = f"tribe:{uuid.uuid4().hex}"
    st.session_state.messages = []

# ---- Sidebar ----
with st.sidebar:
    st.markdown("### Session")
    if st.button("🔄 New conversation"):
        reset_conversation()
        st.rerun()

# ---- Build graph once ----
@st.cache_resource
def get_graph():
    return build_mvp_graph()

graph = get_graph()

# ---- Render history ----
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.write(content)

# ---- Input ----
user_input = st.chat_input("What’s on your mind?")

if user_input:
    st.session_state.messages.append(("user", user_input))
    with st.chat_message("user"):
        st.write(user_input)

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config={"thread_id": st.session_state.thread_id},
    )

    reply = result.get("final_response") or (
        "I’m here with you. Want to say a bit more?"
    )

    st.session_state.messages.append(("assistant", reply))
    with st.chat_message("assistant"):
        st.write(reply)
