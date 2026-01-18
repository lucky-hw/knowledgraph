import os
import requests
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from langchain.schema.runnable import Runnable,RunnableConfig
from typing import Dict, Any
import yaml
from enum import Enum

load_dotenv(".env")
url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
embedding_model_name = os.getenv("EMBEDDING_MODEL")
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'search_prompt.yml')
with open(PROMPT_PATH, 'r') as f:
    search_prompt = yaml.safe_load(f)

class SearchType(Enum):
    product2patent = 1
    product2people = 2
    product2paper = 3


# if Neo4j is local, you can go to http://localhost:7474/ to browse the database
neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)



class BaseLogger:
    def __init__(self) -> None:
        self.info = print


def extract_title_and_question(input_string):
    lines = input_string.strip().split("\n")

    title = ""
    question = ""
    is_question = False  # flag to know if we are inside a "Question" block

    for line in lines:
        if line.startswith("Title:"):
            title = line.split("Title: ", 1)[1].strip()
        elif line.startswith("Question:"):
            question = line.split("Question: ", 1)[1].strip()
            is_question = (
                True  # set the flag to True once we encounter a "Question:" line
            )
        elif is_question:
            # if the line does not start with "Question:" but we are inside a "Question" block,
            # then it is a continuation of the question
            question += "\n" + line.strip()

    return title, question


def create_vector_index(driver) -> None:
    index_query = "CREATE VECTOR INDEX zhiku IF NOT EXISTS FOR (m:Question) ON m.embedding"
    try:
        driver.query(index_query)
    except:  # Already exists
        pass
    index_query = (
        "CREATE VECTOR INDEX top_answers IF NOT EXISTS FOR (m:Answer) ON m.embedding"
    )
    try:
        driver.query(index_query)
    except:  # Already exists
        pass


def create_constraints(driver):
    driver.query(
        "CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE (q.id) IS UNIQUE"
    )
    driver.query(
        "CREATE CONSTRAINT answer_id IF NOT EXISTS FOR (a:Answer) REQUIRE (a.id) IS UNIQUE"
    )
    driver.query(
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE (u.id) IS UNIQUE"
    )
    driver.query(
        "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE (t.name) IS UNIQUE"
    )


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def format_output(outputs):
    # print(outputs)
    print("\n".join(str(outputs[output]) for output in outputs.keys()))
    return "\n".join(str(outputs[output]) for output in outputs.keys())

import re

class NameConverter:
    """
    学术论文英文名转换为拼音顺序
    """
    
    # 扩展的中文姓氏列表
    CHINESE_SURNAMES = {
        'zhang', 'wang', 'li', 'liu', 'chen', 'yang', 'zhao', 'huang',
        'zhou', 'wu', 'xu', 'sun', 'ma', 'zhu', 'hu', 'guo', 'lin',
        'xie', 'song', 'tang', 'he', 'gao', 'zheng', 'luo', 'liang',
        'dong', 'xu', 'cai', 'cao', 'cheng', 'dai', 'fan', 'fang',
        'feng', 'fu', 'gan', 'gong', 'gu', 'han', 'hao', 'hong',
        'hou', 'huang', 'hui', 'jiang', 'jin', 'kang', 'kong', 'lei',
        'liao', 'lu', 'lv', 'meng', 'mo', 'ning', 'ouyang', 'pan',
        'peng', 'qi', 'qian', 'qiao', 'qin', 'qiu', 'qu', 'ran',
        'ren', 'ruan', 'sha', 'shao', 'shen', 'shi', 'shu', 'si',
        'su', 'tan', 'tian', 'tong', 'wan', 'wei', 'wen', 'wu',
        'xi', 'xia', 'xiang', 'xiao', 'xin', 'xing', 'xiong', 'ye',
        'yi', 'yin', 'yu', 'yuan', 'yue', 'zeng', 'zhan', 'zhang',
        'zhao', 'zheng', 'zhong', 'zhou', 'zhu', 'zhuang', 'zou'
    }
    
    @staticmethod
    def clean_name(name):
        """清理和标准化姓名"""
        # 移除特殊字符
        name = re.sub(r'[^\w\s]', '', name)
        # 标准化空格
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    @staticmethod
    def detect_name_format(name):
        """
        检测姓名的格式
        返回: 'western' (名 姓), 'eastern' (姓 名), 或 'unknown'
        """
        parts = name.lower().split()
        if len(parts) < 2:
            return 'unknown'
        
        # 检查第一个词是否为常见中文姓氏
        if parts[0] in NameConverter.CHINESE_SURNAMES:
            return 'eastern'  # 可能是姓在前
        
        # 检查最后一个词是否为常见中文姓氏
        if parts[-1] in NameConverter.CHINESE_SURNAMES:
            return 'western'  # 可能是名在前
        
        return 'unknown'
    
    @staticmethod
    def convert_to_pinyin_order(name):
        """
        将英文论文名转换为拼音顺序
        """
        # 清理姓名
        name = NameConverter.clean_name(name)
        
        # 检测格式
        format_type = NameConverter.detect_name_format(name)
        
        # 分割部分
        parts = name.split()
        
        if len(parts) < 2:
            return name.lower().capitalize()  # 无法转换
        
        # 根据检测到的格式进行转换
        if format_type == 'western':
            # 名 姓 -> 姓 名
            surname = parts[-1].lower()
            given_name = ''.join(parts[:-1]).lower()
                        
            # 格式化：姓首字母大写，名各部分首字母大写
            return f"{surname.capitalize()} {given_name.capitalize()}"
        
        elif format_type == 'eastern':
            # 已经可能是姓 名格式
            # 确保大小写正确
            surname = parts[0].lower()
            given_name = ''.join(parts[1:]).lower()
            
            # 格式化：姓首字母大写，名各部分首字母大写
            return f"{surname.capitalize()} {given_name.capitalize()}"
        
        else:
            # 未知格式，尝试智能转换
            # 假设最后一个词是姓
            surname = parts[-1].lower()
            given_name = ''.join(parts[:-1]).lower()
            
            # 检查姓氏是否看起来像中文姓氏
            if surname.lower() in NameConverter.CHINESE_SURNAMES:
                return f"{surname.capitalize()} {given_name.capitalize()}"
            else:
                # 保持原样
                return name
    
    @staticmethod
    def convert_chinese_name_to_pinyin(name):
        """
        将中文名转换为不同格式的拼音
        
        Args:
            name: 中文名
            return: 
                '张三丰' - Zhang Sanfeng
        """
        from pypinyin import lazy_pinyin, Style
        pinyin_list = lazy_pinyin(name, style=Style.NORMAL)
        if len(pinyin_list) == 0:
            return ""
        surname = pinyin_list[0].lower()
        if len(pinyin_list) == 1:
            return surname.capitalize()
        given_name = ''.join(pinyin_list[1:]).lower()
        return f"{surname.capitalize()} {given_name.capitalize()}"

    @staticmethod
    def convert(name):
        name = NameConverter.clean_name(name)
        chinese_count = sum(1 for char in name if '\u4e00' <= char <= '\u9fff')
        if chinese_count > 0:
            return NameConverter.convert_chinese_name_to_pinyin(name)
        else:
            return NameConverter.convert_to_pinyin_order(name)

def get_patent_content(product_name, params = None):
    query = f"""
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{product_name}\"
    MATCH (p)-[:属于]->(c:公司)
    MATCH (z:专利)-[:申请人]->(c)
    RETURN {{patent: z}}
    LIMIT $limit
    """
    if params is None:
        params = {"limit": 100}
    print("neo4j query:\n", query)
    res = neo4j_graph.query(query, params)
    # print("neo4j res:\n", res)
    return res

def get_patent_people(product_name, params = None):
    query = f"""
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{product_name}\"
    MATCH (p)-[:属于]->(c:公司)
    MATCH (z:专利)-[:申请人]->(c)
    MATCH (p1:人员)-[r:发表]->(z)
    RETURN {{
        person : p1,
        relationship: {{
            type: type(r),
            properties: properties(r)
        }},
        patent: z}}
    LIMIT $limit
    """
    if params is None:
        params = {"limit": 100}
    print("neo4j query:\n", query)
    res = neo4j_graph.query(query, params)
    # print("neo4j res:\n", res)
    return res


def get_papers(product_name, params = None):
    query = f"""
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{product_name}\"
    MATCH (p)-[:属于]->(c:公司)
    MATCH (p1:人员)-[:任职]->(c)
    MATCH (p2:人员)-[:相似]->(p1)
    MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    MATCH (person)-[r:发表]->(pa:论文)
    RETURN {{
        person : person,
        relationship: {{
            type: type(r),
            properties: properties(r)
        }},
        paper: pa}}
    LIMIT $limit
    """
    if params is None:
        params = {"limit": 100}
    print("neo4j query:\n", query)
    res = neo4j_graph.query(query, params)
    # print("neo4j res:\n", res)
    return res

def get_template(searchType):
    return search_prompt["zhiku"]["prompt"][SearchType(searchType).name]

class Neo4jQueryRunnable(Runnable):    
    def __init__(self, searchType, cypher_query: str = None):
        if SearchType(searchType).name == "product2patent":
            self.query_func = get_patent_content
        elif SearchType(searchType).name == "product2people":
            self.query_func = get_patent_people
        elif SearchType(searchType).name == "product2paper":
            self.query_func = get_papers
        else:
            pass
        self.cypher_query = cypher_query
        self.prompt = get_template(searchType)
    
    def invoke(self, input_dict: Dict[str, Any], config: RunnableConfig = None):
        # 从输入获取查询，或使用预设查询
        if isinstance(input_dict, str):
            query = input_dict
            prompt = self.prompt
        elif isinstance(input_dict, dict):
            query = input_dict.get("question", self.cypher_query)
            prompt = input_dict.get("prompt", self.prompt)
            if not query:
                # 如果输入中有问题，可以自动生成查询
                question = input_dict.get("question", "")
                # 这里可以添加自然语言转Cypher的逻辑
                query = f"MATCH (n) WHERE n.name CONTAINS '{question}' RETURN n LIMIT 5"
        else:
            query = self.cypher_query
            prompt = self.prompt
        result = self.query_func(query.strip())
        return {"prompt": prompt + "\n----", "search_result": result}