import torch
import os
import requests
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
import streamlit as st
from streamlit.logger import get_logger
from chains import load_embedding_model
from utils import create_constraints, create_vector_index, NameConverter
from PIL import Image
import json
load_dotenv(".env")

url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
embedding_model_name = os.getenv("EMBEDDING_MODEL")

logger = get_logger(__name__)

so_api_base_url = "https://api.stackexchange.com/2.3/search/advanced"

embeddings, dimension = load_embedding_model(
    embedding_model_name, config={"ollama_base_url": ollama_base_url}, logger=logger
)

# if Neo4j is local, you can go to http://localhost:7474/ to browse the database
neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)

create_constraints(neo4j_graph)
create_vector_index(neo4j_graph)
name_converter = NameConverter()

def load_zhiku_data(tag: str = "company", filecontent: str = "") -> None:
    data = json.loads(filecontent)
    if tag =="company":
        insert_company_data(data)
    elif tag =="product":
        insert_product_data(data)
    elif tag =="paper":
        insert_paper_data(data)
    elif tag =="patent":
        insert_patent_data(data)
    else:
        return



def insert_company_data(data: dict) -> None:
    for company in data["company"]:
        import_query = ""
        import_query += "MERGE (company:公司 {名称: \""+ company["公司名称"] +"\"})\n"
        import_query += "MERGE (person1:人员 {姓名: \""+ company["法定代表人"] + "\"})\n"
        import_query += "MERGE (people1:人员 {姓名: \""+ name_converter.convert(company["法定代表人"]) + "\"})\n"
        import_query += "MERGE (person1)-[:相似 {命名: \"中转英\"}]->(people1)\n"
        import_query += "MERGE (people1)-[:相似 {命名: \"英转中\"}]->(person1)\n"
        import_query += "MERGE (person1)-[:任职 {职位: \"法定代表人\"}]->(company)\n"
        distint_id = 10       
        for id, people in enumerate(company["股东名称"]):
            if "公司" in people:
                import_query += "MERGE (company" + str(distint_id) + ":公司 {名称: \""+ people +"\"})\n"
                import_query += "MERGE (company" + str(distint_id) + ")-[:任职 {职位: \"股东\"}]->(company)\n"
            else:
                import_query += "MERGE (person"+ str(distint_id) +":人员 {姓名: \""+ people +"\"})\n"
                import_query += "MERGE (people"+ str(distint_id) +":人员 {姓名: \""+ name_converter.convert(people) +"\"})\n"
                import_query += "MERGE (person"+ str(distint_id) +")-[:相似 {命名: \"中转英\"}]->(people"+ str(distint_id) +")\n"
                import_query += "MERGE (people"+ str(distint_id) +")-[:相似 {命名: \"英转中\"}]->(person"+ str(distint_id) +")\n"
                import_query += "MERGE (person"+ str(distint_id) +")-[:任职 {职位: \"股东\"}]->(company)\n"
            distint_id += 1
        for id, people in enumerate(company["主要人员"]):
            import_query += "MERGE (person"+ str(distint_id) +":人员 {姓名: \""+ people +"\"})\n"
            import_query += "MERGE (people"+ str(distint_id) +":人员 {姓名: \""+ name_converter.convert(people) +"\"})\n"
            import_query += "MERGE (person"+ str(distint_id) +")-[:相似 {命名: \"中转英\"}]->(people"+ str(distint_id) +")\n"
            import_query += "MERGE (people"+ str(distint_id) +")-[:相似 {命名: \"英转中\"}]->(person"+ str(distint_id) +")\n"
            import_query += "MERGE (person"+ str(distint_id) +")-[:任职 {职位: \"主要人员\"}]->(company)\n"
            distint_id += 1
        neo4j_graph.query(import_query)

def insert_product_data(data: dict) -> None:
    for product in data["product"]:
        import_query = ""
        import_query += "MERGE (product:产品 {名称: \""+ product["产品名称"] +"\"})\n"
        import_query += "MERGE (company:公司 {名称: \""+ product["注册人名称"] + "\"})\n"
        import_query += "MERGE (product)-[:属于]->(company)\n"
        import_query += "MERGE (place:地址 {名称:\""+ product["注册人住所"] + "\"})\n"
        import_query += "MERGE (product)-[:位置]->(place)\n"
        import_query += "SET product.组成 = \""+ product["结构及组成/主要组成成分"] + "\"\n"
        import_query += "SET product.用途 = \""+ product["适用范围/预期用途"] + "\"\n"
        neo4j_graph.query(import_query)

def insert_paper_data(data: dict) -> None:
    for paper in data["papers"]:
        import_query = ""
        import_query += "MERGE (paper:论文 {名称: \""+ paper["Title"] +"\"})\n"
        import_query += "MERGE (person1:人员 {姓名: \""+ paper["first author"] + "\"})\n"
        import_query += "MERGE (people1:人员 {姓名: \""+ name_converter.convert(paper["first author"]) + "\"})\n"
        import_query += "MERGE (person1)-[:相似 {命名: \"中转英\"}]->(people1)\n"
        import_query += "MERGE (people1)-[:相似 {命名: \"英转中\"}]->(person1)\n"
        import_query += "MERGE (person1)-[:发表 {角色: \"主要作者\"}]->(paper)\n"
        distint_id = 10       
        for aff in paper["first author's affiliations"]:
            import_query += "MERGE (company" + str(distint_id) + ":公司 {名称: \""+ aff + "\"})\n"
            import_query += "MERGE (person1)-[:属于 {角色: \"归属单位\"}]->(company" + str(distint_id) + ")\n"
            distint_id += 1    
        for id, people in enumerate(paper["co-first author"]):
            import_query += "MERGE (person"+ str(distint_id) +":人员 {姓名: \""+ people +"\"})\n"
            import_query += "MERGE (people"+ str(distint_id) +":人员 {姓名: \""+ name_converter.convert(people) +"\"})\n"
            import_query += "MERGE (person"+ str(distint_id) +")-[:相似 {命名: \"中转英\"}]->(people"+ str(distint_id) +")\n"
            import_query += "MERGE (people"+ str(distint_id) +")-[:相似 {命名: \"英转中\"}]->(person"+ str(distint_id) +")\n"
            tmp_id = distint_id
            distint_id += 1
            import_query += "MERGE (person" + str(tmp_id) + ")-[:发表 {角色: \"其他作者\"}]->(paper)\n"
            for aff in paper["co-first author's affiliations"][id]:
                import_query += "MERGE (company" + str(distint_id) + ":公司 {名称: \""+ aff + "\"})\n"
                import_query += "MERGE (person" + str(tmp_id) + ")-[:属于 {角色: \"归属单位\"}]->(company" + str(distint_id) + ")\n"
                distint_id += 1
        import_query += "SET paper.摘要 = \""+ paper["abstract"] + "\"\n"
        neo4j_graph.query(import_query)

def insert_patent_data(data: dict) -> None:
    for patent in data["patents"]:
        import_query = ""
        import_query += "MERGE (patent:专利 {名称: \""+ patent["专利名称"] +"\"})\n"
        import_query += "MERGE (person1:人员 {姓名: \""+ patent["第一发明人"] + "\"})\n"
        import_query += "MERGE (people1:人员 {姓名: \""+ name_converter.convert(patent["第一发明人"]) + "\"})\n"
        import_query += "MERGE (person1)-[:相似 {命名: \"中转英\"}]->(people1)\n"
        import_query += "MERGE (people1)-[:相似 {命名: \"英转中\"}]->(person1)\n"
        import_query += "MERGE (person1)-[:发表 {角色: \"第一发明人\"}]->(patent)\n"
        import_query += "MERGE (company1:公司 {名称: \""+ patent["当前权利人"] +"\"})\n"
        import_query += "MERGE (company2:公司 {名称: \""+ patent["申请人"] +"\"})\n"
        import_query += "MERGE (place:地址 {名称:\""+ patent["申请人地址"] + "\"})\n"
        import_query += "MERGE (patent)-[:申请人地址]->(place)\n"
        import_query += "MERGE (patent)-[:当前权利人]->(company1)\n"
        import_query += "MERGE (patent)-[:申请人]->(company2)\n"
        distint_id = 10       
        for id, people in enumerate(patent["其他发明人"]):
            import_query += "MERGE (person"+ str(distint_id) +":人员 {姓名: \""+ people +"\"})\n"
            import_query += "MERGE (people"+ str(distint_id) +":人员 {姓名: \""+ name_converter.convert(people) +"\"})\n"
            import_query += "MERGE (person"+ str(distint_id) +")-[:相似 {命名: \"中转英\"}]->(people"+ str(distint_id) +")\n"
            import_query += "MERGE (people"+ str(distint_id) +")-[:相似 {命名: \"英转中\"}]->(person"+ str(distint_id) +")\n"
            import_query += "MERGE (person" + str(distint_id) + ")-[:发表 {角色: \"其他发明人\"}]->(patent)\n"
            distint_id += 1
        import_query += "SET patent.摘要 = \""+ patent["摘要"] + "\"\n"
        import_query += "SET patent.主权利要求 = \""+ patent["主权利要求"] + "\"\n"
        neo4j_graph.query(import_query)

# Streamlit
def get_tag() -> str:
    input_text = st.text_input(
        "Which tag context do you want to import?1. company; 2. product; 3.paper; 4.patent", value="company"
    )
    return input_text


def get_files():
    uploaded_file = st.file_uploader("Upload your file")
    return uploaded_file


def render_page():
    datamodel_image = Image.open("./images/datamodel.png")
    st.header("Zhiku Loader")
    st.subheader("Choose Zhiku tags to load into Neo4j")
    st.caption("Go to http://localhost:7474/ to explore the graph.")

    user_input = get_tag()
    uploaded_file = get_files()

    if st.button("Import", type="primary"):
        with st.spinner("Loading... This might take a minute or two."):
            try:
                if uploaded_file is not None:
                    file_content = uploaded_file.getvalue().decode("utf-8")
                load_zhiku_data(user_input, file_content)
                st.success("Import successful", icon="✅")
                st.caption("Data model")
                st.image(datamodel_image)
                st.caption("Go to http://localhost:7474/ to interact with the database")
            except Exception as e:
                st.error(f"Error: {e}", icon="🚨")
                raise e

render_page()
