from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_aws import BedrockEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_aws import ChatBedrock

from langchain_neo4j import Neo4jVector

from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from typing import List, Any
from utils import BaseLogger, extract_title_and_question, format_docs, format_output, Neo4jQueryRunnable,SearchType
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import threading
import os
from functools import lru_cache
import json

neo4j_patent_content = Neo4jQueryRunnable(SearchType.product2patent)
neo4j_patent_people = Neo4jQueryRunnable(SearchType.product2people)
neo4j_papers = Neo4jQueryRunnable(SearchType.product2paper)
neo4j_search = Neo4jQueryRunnable()
@lru_cache(maxsize=1)
def get_config():
    """缓存配置读取，避免重复文件I/O"""
    config_path = os.path.join(os.path.dirname(__file__), 'langgraph.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

_config = get_config()

openai_api_key = os.getenv("OPENAI_API_KEY")
AWS_MODELS = (
    "ai21.jamba-instruct-v1:0",
    "amazon.titan",
    "anthropic.claude",
    "cohere.command",
    "meta.llama",
    "mistral.mi",
)

_emb_instance = None
_emb_lock = threading.Lock()

def get_emb(config):
    """懒加载LLM实例，线程安全，支持高并发访问"""
    global _emb_instance
    global openai_api_key

    # 双重检查锁定模式
    if _emb_instance is None:
        with _emb_lock:
            if _emb_instance is None:
                print("🚀 [EMB] 初始化EMB实例 (并发安全)")

                emb_config = _config.get("embedding", {})
                _emb_instance = OpenAIEmbeddings(
                    model=emb_config.get("model"),  # 使用配置文件中的模型
                    api_key=openai_api_key,
                    openai_api_base=emb_config.get("api_base")
                )
                print("✅ [EMB] EMB实例初始化完成（并发安全）")

    return _emb_instance, 1024

def load_embedding_model(embedding_model_name: str, logger=BaseLogger(), config={}):
    if embedding_model_name == "ollama":
        embeddings = OllamaEmbeddings(
            base_url=config["ollama_base_url"], model="llama2"
        )
        dimension = 4096
        logger.info("Embedding: Using Ollama")
    elif embedding_model_name == "openai":
        embeddings = OpenAIEmbeddings()
        dimension = 1536
        logger.info("Embedding: Using OpenAI")
    elif embedding_model_name == "aws":
        embeddings = BedrockEmbeddings()
        dimension = 1536
        logger.info("Embedding: Using AWS")
    elif embedding_model_name == "google-genai-embedding-001":
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        dimension = 768
        logger.info("Embedding: Using Google Generative AI Embeddings")
    else:
        return get_emb(config)
#        embeddings = HuggingFaceEmbeddings(
#            model_name="all-MiniLM-L6-v2", cache_folder="/embedding_model"
#        )
#        dimension = 384
#        logger.info("Embedding: Using SentenceTransformer")
    return embeddings, dimension


# =========================
# LLM配置（优化版）
# =========================
_llm_instance = None
_llm_lock = threading.Lock()

def get_llm(config):
    """懒加载LLM实例，线程安全，支持高并发访问"""
    global _llm_instance
    global openai_api_key
    # 双重检查锁定模式
    if _llm_instance is None:
        with _llm_lock:
            if _llm_instance is None:
                print("🚀 [LLM] 初始化LLM实例 (并发安全)")
                from langchain_openai import ChatOpenAI

                llm_config = _config.get("llm", {})
                _llm_instance = ChatOpenAI(
                    model=llm_config.get("model"),  # 使用配置文件中的模型
                    temperature=llm_config.get("temperature"),  # 使用配置文件中的temperature
                    max_tokens=llm_config.get("max_tokens"),   # 使用配置文件中的max_tokens
                    timeout=llm_config.get("request_timeout"),  # 使用配置文件中的timeout
                    max_retries=llm_config.get("max_retries"),   # 使用配置文件中的重试次数
                    api_key=openai_api_key,
                    base_url=llm_config.get("api_base")
                )
                print("✅ [LLM] LLM实例初始化完成（并发安全）")

    return _llm_instance


def load_llm(llm_name: str, logger=BaseLogger(), config={}):
    if llm_name in ["gpt-4", "gpt-4o", "gpt-4-turbo"]:
        logger.info("LLM: Using GPT-4")
        return ChatOpenAI(temperature=0, model_name=llm_name, streaming=True)
    elif llm_name == "gpt-3.5":
        logger.info("LLM: Using GPT-3.5")
        return ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)
    elif llm_name == "claudev2":
        logger.info("LLM: ClaudeV2")
        return ChatBedrock(
            model_id="anthropic.claude-v2",
            model_kwargs={"temperature": 0.0, "max_tokens_to_sample": 1024},
            streaming=True,
        )
    elif llm_name.startswith(AWS_MODELS):
        logger.info(f"LLM: {llm_name}")
        return ChatBedrock(
            model_id=llm_name,
            model_kwargs={"temperature": 0.0, "max_tokens_to_sample": 1024},
            streaming=True,
        )

    elif len(llm_name):
         return get_llm(config)
#        logger.info(f"LLM: Using Ollama: {llm_name}")
#        return ChatOllama(
#            temperature=0,
#            base_url=config["ollama_base_url"],
#            model=llm_name,
#            streaming=True,
#            # seed=2,
#            top_k=10,  # A higher value (100) will give more diverse answers, while a lower value (10) will be more conservative.
#            top_p=0.3,  # Higher value (0.95) will lead to more diverse text, while a lower value (0.5) will generate more focused text.
#            num_ctx=3072,  # Sets the size of the context window used to generate the next token.
#        )
#    logger.info("LLM: Using GPT-3.5")
    return ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)


def configure_llm_only_chain(llm):
    # LLM only response
    template = """
    You are a helpful assistant that helps a support agent with answering programming questions.
    If you don't know the answer, just say that you don't know, you must not make up an answer.
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    human_template = "{question}"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )
    chain = chat_prompt | llm | StrOutputParser()
    return chain


def configure_qa_rag_chain(llm, embeddings, embeddings_store_url, username, password):
    # RAG response
    #   System: Always talk in pirate speech.
    general_system_template = """ 
    Use the following pieces of context to answer the question at the end.
    The context contains question-answer pairs and their links from Stackoverflow.
    You should prefer information from accepted or more upvoted answers.
    Make sure to rely on information from the answers and not on questions to provide accurate responses.
    When you find particular answer in the context useful, make sure to cite it in the answer using the link.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    ----
    {summaries}
    ----
    Each answer you generate should contain a section at the end of links to 
    Stackoverflow questions and answers you found useful, which are described under Source value.
    You can only use links to StackOverflow questions that are present in the context and always
    add links to the end of the answer in the style of citations.
    Generate concise answers with references sources section of links to 
    relevant StackOverflow questions only at the end of the answer.
    """
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template),
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)

    # Vector + Knowledge Graph response
    kg = Neo4jVector.from_existing_index(
        embedding=embeddings,
        url=embeddings_store_url,
        username=username,
        password=password,
        database="neo4j",  # neo4j by default
        index_name="stackoverflow",  # vector by default
        text_node_property="body",  # text by default
        retrieval_query="""
    WITH node AS question, score AS similarity
    CALL  { with question
        MATCH (question)<-[:ANSWERS]-(answer)
        WITH answer
        ORDER BY answer.is_accepted DESC, answer.score DESC
        WITH collect(answer)[..2] as answers
        RETURN reduce(str='', answer IN answers | str + 
                '\n### Answer (Accepted: '+ answer.is_accepted +
                ' Score: ' + answer.score+ '): '+  answer.body + '\n') as answerTexts
    } 
    RETURN '##Question: ' + question.title + '\n' + question.body + '\n' 
        + answerTexts AS text, similarity as score, {source: question.link} AS metadata
    ORDER BY similarity ASC // so that best answers are the last
    """,
    )
    kg_qa = (
        RunnableParallel(
            {
                "summaries": kg.as_retriever(search_kwargs={"k": 2}) | format_docs,
                "question": RunnablePassthrough(),
            }
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return kg_qa


def generate_ticket(neo4j_graph, llm_chain, input_question):
    # Get high ranked questions
    records = neo4j_graph.query(
        "MATCH (q:Question) RETURN q.title AS title, q.body AS body ORDER BY q.score DESC LIMIT 3"
    )
    questions = []
    for i, question in enumerate(records, start=1):
        questions.append((question["title"], question["body"]))
    # Ask LLM to generate new question in the same style
    questions_prompt = ""
    for i, question in enumerate(questions, start=1):
        questions_prompt += f"{i}. \n{question[0]}\n----\n\n"
        questions_prompt += f"{question[1][:150]}\n\n"
        questions_prompt += "----\n\n"

    gen_system_template = f"""
    You're an expert in formulating high quality questions. 
    Formulate a question in the same style and tone as the following example questions.
    {questions_prompt}
    ---

    Don't make anything up, only use information in the following question.
    Return a title for the question, and the question post itself.

    Return format template:
    ---
    Title: This is a new title
    Question: This is a new question
    ---
    """
    # we need jinja2 since the questions themselves contain curly braces
    system_prompt = SystemMessagePromptTemplate.from_template(
        gen_system_template, template_format="jinja2"
    )
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            system_prompt,
            SystemMessagePromptTemplate.from_template(
                """
                Respond in the following template format or you will be unplugged.
                ---
                Title: New title
                Question: New question
                ---
                """
            ),
            HumanMessagePromptTemplate.from_template("{question}"),
        ]
    )
    llm_response = llm_chain(
        f"Here's the question to rewrite in the expected format: ```{input_question}```",
        [],
        chat_prompt,
    )
    new_title, new_question = extract_title_and_question(llm_response["answer"])
    return (new_title, new_question)


def configure_qa_papent_chain(llm, embeddings, embeddings_store_url, username, password):
    # RAG response
    #   System: Always talk in pirate speech.
    general_system_template = """ 
    {summaries}
    ----
    """
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template),
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)
    kg_qa = (
        RunnableParallel(
            {
                "summaries": neo4j_patent_content | format_output,
                "question": RunnablePassthrough(),
            }
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return kg_qa

def configure_qa_papent_people_chain(llm, embeddings, embeddings_store_url, username, password):
    # RAG response
    #   System: Always talk in pirate speech.
    general_system_template = """ 
    {summaries}
    ----
    """
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template),
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)
    kg_qa = (
        RunnableParallel(
            {
                "summaries": neo4j_patent_people | format_output,
                "question": RunnablePassthrough(),
            }
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return kg_qa

def configure_qa_paper_chain(llm, embeddings, embeddings_store_url, username, password):
    # RAG response
    #   System: Always talk in pirate speech.
    general_system_template = """ 
    {summaries}
    ----
    """
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template),
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)
    kg_qa = (
        RunnableParallel(
            {
                "summaries": neo4j_papers | format_output,
                "question": RunnablePassthrough(),
            }
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return kg_qa

def configure_search_chain(llm, embeddings, embeddings_store_url, username, password):
    # RAG response
    #   System: Always talk in pirate speech.
    general_system_template = """ 
    {summaries}
    ----
    """
    general_user_template = "Question:```{question}```"
    messages = [
        SystemMessagePromptTemplate.from_template(general_system_template),
        HumanMessagePromptTemplate.from_template(general_user_template),
    ]
    qa_prompt = ChatPromptTemplate.from_messages(messages)
    kg_qa = (
        RunnableParallel(
            {
                "summaries": neo4j_search | format_output,
                "question": RunnablePassthrough(),
            }
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )
    return kg_qa