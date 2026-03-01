import os

import streamlit as st
from streamlit.logger import get_logger
import torch
torch.classes.__path__ = [os.path.join(torch.__path__[0], torch.classes.__file__)] 
from langchain.callbacks.base import BaseCallbackHandler
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv
from utils import create_vector_index, SearchType
from chains import (
    load_embedding_model,
    load_llm,
    configure_llm_only_chain,
    configure_qa_rag_chain,
    generate_ticket,
    configure_qa_papent_chain,
    configure_qa_papent_people_chain,
    configure_qa_paper_chain,
    configure_search_chain
)

load_dotenv(".env")

url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
embedding_model_name = os.getenv("EMBEDDING_MODEL")
llm_name = os.getenv("LLM")
# Remapping for Langchain Neo4j integration
os.environ["NEO4J_URL"] = url

logger = get_logger(__name__)

# if Neo4j is local, you can go to http://localhost:7474/ to browse the database
neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)
embeddings, dimension = load_embedding_model(
    embedding_model_name, config={"ollama_base_url": ollama_base_url}, logger=logger
)
create_vector_index(neo4j_graph)


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)


llm = load_llm(llm_name, logger=logger, config={"ollama_base_url": ollama_base_url})




llm_chain = configure_llm_only_chain(llm)
rag_chain = configure_qa_rag_chain(
    llm, embeddings, embeddings_store_url=url, username=username, password=password
)
search_total = configure_search_chain(
    llm, embeddings, embeddings_store_url=url, username=username, password=password
)

# patent_search = configure_qa_papent_chain(
#     llm, embeddings, embeddings_store_url=url, username=username, password=password
# )
# people_search = configure_qa_papent_people_chain(
#     llm, embeddings, embeddings_store_url=url, username=username, password=password
# )
# paper_search = configure_qa_paper_chain(
#     llm, embeddings, embeddings_store_url=url, username=username, password=password
# )


# Streamlit UI
styl = f"""
<style>
    /* not great support for :has yet (hello FireFox), but using it for now */
    .element-container:has([aria-label="Select RAG mode"]) {{
      position: fixed;
      bottom: 33px;
      background: white;
      z-index: 101;
    }}
    .stChatFloatingInputContainer {{
        bottom: 20px;
    }}

    /* Generate ticket text area */
    textarea[aria-label="Description"] {{
        height: 200px;
    }}

    .element-container:has([aria-label="What coding issue can I help you resolve today?"]) {{
        bottom: 45px;
    }} 
</style>
"""
st.markdown(styl, unsafe_allow_html=True)

# 自定义双输入组件
def dual_chat_input(key1="input1", key2="input2", placeholder1="第一个输入...", placeholder2="第二个输入..."):
    """创建一个双输入组件"""
    
    # 创建容器
    input_container = st.container()
    
    with input_container:
        # 使用columns布局
        col1, col2, col3 = st.columns([4, 4, 1])
        
        with col1:
            input1 = st.text_input(
                label="",
                placeholder=placeholder1,
                key=f"{key1}_chat",
                label_visibility="collapsed"
            )
        
        with col2:
            input2 = st.text_input(
                label="",
                placeholder=placeholder2,
                key=f"{key2}_chat",
                label_visibility="collapsed"
            )
        
        with col3:
            submit_clicked = st.button("提交", type="primary", use_container_width=True)
    
    return input1, input2, submit_clicked



def mode_select() -> str:
    options = [member.name for member in SearchType]
    return st.radio("Select mode", options, horizontal=True)


name = mode_select()
output_function = search_total

if "generated" not in st.session_state:
    st.session_state[f"generated"] = []

if "user_input" not in st.session_state:
    st.session_state[f"user_input"] = []

if "rag_mode" not in st.session_state:
    st.session_state[f"rag_mode"] = []

if "user_prompt" not in st.session_state:
    st.session_state[f"user_prompt"] = []


def chat_input():
    global name
    user_input, user_prompt, submitted = dual_chat_input(
        placeholder1="输入产品名。",
        placeholder2="输入prompt。无输入则用默认"
    )

    if submitted and (user_input or user_prompt):
        stream_handler = StreamHandler(st.empty())
        if user_input:
            if user_prompt:
                output = output_function.invoke(
                    {"question":user_input, "prompt": user_prompt,"searchType": name}, config={"callbacks": [stream_handler]}
                )
            else:
                output = output_function.invoke(
                    {"question":user_input,"searchType": name}, config={"callbacks": [stream_handler]}
                )
                user_prompt =" "
        else:
            user_input =" "

        st.session_state[f"user_input"].append(user_input)
        st.session_state[f"generated"].append(output)
        st.session_state[f"rag_mode"].append(name)
        st.session_state[f"user_prompt"].append(user_prompt)
        display_chat()

def display_chat():
    # Session state
    if len(st.session_state[f"generated"]) > 0:
        length = len(st.session_state[f"generated"])
        size = len(st.session_state[f"generated"])
        # Display only the last three exchanges
        for i in range(max(size - 3, 0), size):
            with st.chat_message("user"):
                st.write(st.session_state[f"user_input"][i])
            with st.chat_message("user"):
                st.write(st.session_state[f"user_prompt"][i])

            with st.chat_message("assistant"):
                st.caption(f"RAG: {st.session_state[f'rag_mode'][i]}")
                st.write(st.session_state[f"generated"][i])

        with st.container():
            st.write("&nbsp;")

def open_sidebar():
    st.session_state.open_sidebar = True


def close_sidebar():
    st.session_state.open_sidebar = False


if not "open_sidebar" in st.session_state:
    st.session_state.open_sidebar = False
if st.session_state.open_sidebar:
    new_title, new_question = generate_ticket(
        neo4j_graph=neo4j_graph,
        llm_chain=llm_chain,
        input_question=st.session_state[f"user_input"][-1],
    )
    with st.sidebar:
        st.title("Ticket draft")
        st.write("Auto generated draft ticket")
        st.text_input("Title", new_title)
        st.text_area("Description", new_question)
        st.button(
            "Submit to support team",
            type="primary",
            key="submit_ticket",
            on_click=close_sidebar,
        )

chat_input()