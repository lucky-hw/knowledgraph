import os
import json
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
import streamlit as st
from streamlit.logger import get_logger
from utils import create_constraints, create_vector_index, NameConverter
from PIL import Image

load_dotenv(".env")

url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

logger = get_logger(__name__)


neo4j_graph = Neo4jGraph(
    url=url, username=username, password=password, refresh_schema=False
)

create_constraints(neo4j_graph)
create_vector_index(neo4j_graph)
name_converter = NameConverter()


def _cy_escape(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def load_zhiku_data(tag: str = "company", filecontent: str = "") -> None:
    data = json.loads(filecontent)
    tag = (tag or "").strip().lower()
    if tag == "company":
        insert_company_data(data)
    elif tag == "product":
        insert_product_data(data)
    elif tag =="paper":
        insert_paper_data(data)
    elif tag == "patent":
        insert_patent_data(data)
    elif tag == "expert":
        insert_expert_data(data)
    elif tag == "competition":
        insert_competition_data(data)
    elif tag == "scholar_kg":
        insert_scholar_kg_data(data)
    elif tag == "paper2author":
        insert_paper2author_data(data)


def load_all_browse_data(base_dir: str | None = None) -> None:
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_data")
    sequence = [
        ("entity/company.json", "company"),
        ("entity/product.json", "product"),
        ("entity/paper.json", "paper"),
        ("entity/paper2.json", "paper"),
        ("entity/patent.json", "patent"),
        ("entity/patent2.json", "patent"),
        ("entity/people.json", "expert"),
        ("entity/competition.json", "competition"),
        ("entity/scholar_kg.json", "scholar_kg"),
        ("edge/paper2author.json", "paper2author"),
    ]
    for rel, tag in sequence:
        path = os.path.join(base_dir, rel)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                load_zhiku_data(tag, f.read())


def insert_company_data(data: dict) -> None:
    for company in data["company"]:
        import_query = ""
        import_query += (
            'MERGE (company:公司 {名称: "'
            + _cy_escape(company["公司名称"])
            + '"})\n'
        )
        import_query += (
            'MERGE (person1:人员 {姓名: "'
            + _cy_escape(company["法定代表人"])
            + '"})\n'
        )
        conv = _cy_escape(name_converter.convert(company["法定代表人"]))
        import_query += 'MERGE (people1:人员 {姓名: "' + conv + '"})\n'
        import_query += 'MERGE (person1)-[:相似 {命名: "中转英"}]->(people1)\n'
        import_query += 'MERGE (people1)-[:相似 {命名: "英转中"}]->(person1)\n'
        import_query += 'MERGE (person1)-[:任职 {职位: "法定代表人"}]->(company)\n'
        if company.get("关联依据"):
            import_query += (
                'SET company.关联依据 = "'
                + _cy_escape(company["关联依据"])
                + '"\n'
            )
        for key in ("成立日期", "注册资本", "统一社会信用代码"):
            if company.get(key):
                import_query += (
                    "SET company.`"
                    + key
                    + '` = "'
                    + _cy_escape(company[key])
                    + '"\n'
                )
        distint_id = 10
        for people in company.get("股东名称") or []:
            if "公司" in people:
                import_query += (
                    "MERGE (company"
                    + str(distint_id)
                    + ':公司 {名称: "'
                    + _cy_escape(people)
                    + '"})\n'
                )
                import_query += (
                    "MERGE (company"
                    + str(distint_id)
                    + ')-[:任职 {职位: "股东"}]->(company)\n'
                )
            else:
                import_query += (
                    "MERGE (person"
                    + str(distint_id)
                    + ':人员 {姓名: "'
                    + _cy_escape(people)
                    + '"})\n'
                )
                import_query += (
                    "MERGE (people"
                    + str(distint_id)
                    + ':人员 {姓名: "'
                    + _cy_escape(name_converter.convert(people))
                    + '"})\n'
                )
                import_query += (
                    "MERGE (person"
                    + str(distint_id)
                    + ')-[:相似 {命名: "中转英"}]->(people'
                    + str(distint_id)
                    + ")\n"
                )
                import_query += (
                    "MERGE (people"
                    + str(distint_id)
                    + ')-[:相似 {命名: "英转中"}]->(person'
                    + str(distint_id)
                    + ")\n"
                )
                import_query += (
                    "MERGE (person"
                    + str(distint_id)
                    + ')-[:任职 {职位: "股东"}]->(company)\n'
                )
            distint_id += 1
        for people in company.get("主要人员") or []:
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(people)
                + '"})\n'
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(name_converter.convert(people))
                + '"})\n'
            )
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ')-[:相似 {命名: "中转英"}]->(people'
                + str(distint_id)
                + ")\n"
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ')-[:相似 {命名: "英转中"}]->(person'
                + str(distint_id)
                + ")\n"
            )
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ')-[:任职 {职位: "主要人员"}]->(company)\n'
            )
            distint_id += 1
        neo4j_graph.query(import_query)

    for company in data["company"]:
        rivals = company.get("竞品公司") or []
        if not rivals:
            continue
        anchor = (company.get("公司名称") or "").strip()
        note = (company.get("竞品说明") or "竞品关系").strip()
        for rival in rivals:
            rname = (rival or "").strip()
            if not rname:
                continue
            neo4j_graph.query(
                """
                MATCH (a:公司 {名称: $anchor})
                MATCH (b:公司 {名称: $rival})
                MERGE (a)-[x:竞品]->(b)
                SET x.说明 = $note
                MERGE (b)-[y:竞品]->(a)
                SET y.说明 = $note
                """,
                {"anchor": anchor, "rival": rname, "note": note},
            )


def insert_product_data(data: dict) -> None:
    for product in data["product"]:
        import_query = ""
        import_query += (
            'MERGE (product:产品 {名称: "'
            + _cy_escape(product["产品名称"])
            + '"})\n'
        )
        import_query += (
            'MERGE (company:公司 {名称: "'
            + _cy_escape(product["注册人名称"])
            + '"})\n'
        )
        import_query += "MERGE (product)-[:属于]->(company)\n"
        import_query += (
            'MERGE (place:地址 {名称:"'
            + _cy_escape(product["注册人住所"])
            + '"})\n'
        )
        import_query += "MERGE (product)-[:位置]->(place)\n"
        import_query += (
            'SET product.组成 = "'
            + _cy_escape(product["结构及组成/主要组成成分"])
            + '"\n'
        )
        import_query += (
            'SET product.用途 = "'
            + _cy_escape(product["适用范围/预期用途"])
            + '"\n'
        )
        if product.get("注册证编号"):
            import_query += (
                'SET product.注册证编号 = "'
                + _cy_escape(product["注册证编号"])
                + '"\n'
            )
        if product.get("生产地址"):
            import_query += (
                'SET product.生产地址 = "'
                + _cy_escape(product["生产地址"])
                + '"\n'
            )
        if product.get("管理类别"):
            import_query += (
                'SET product.管理类别 = "'
                + _cy_escape(product["管理类别"])
                + '"\n'
            )
        if product.get("审批部门"):
            import_query += (
                'SET product.审批部门 = "'
                + _cy_escape(product["审批部门"])
                + '"\n'
            )
        if product.get("型号规格"):
            import_query += (
                'SET product.型号规格 = "'
                + _cy_escape(product["型号规格"])
                + '"\n'
            )
        if product.get("批准日期"):
            import_query += (
                'SET product.批准日期 = "'
                + _cy_escape(product["批准日期"])
                + '"\n'
            )
        if product.get("有效期"):
            import_query += (
                'SET product.有效期 = "'
                + _cy_escape(product["有效期"])
                + '"\n'
            )
        if product.get("关联依据"):
            import_query += (
                'SET product.关联依据 = "'
                + _cy_escape(product["关联依据"])
                + '"\n'
            )
        neo4j_graph.query(import_query)


def insert_paper_data(data: dict) -> None:
    for paper in data["papers"]:
        import_query = ""
        import_query += (
            'MERGE (paper:论文 {名称: "' + _cy_escape(paper["Title"]) + '"})\n'
        )
        import_query += (
            'MERGE (person1:人员 {姓名: "'
            + _cy_escape(paper["first author"])
            + '"})\n'
        )
        import_query += (
            'MERGE (people1:人员 {姓名: "'
            + _cy_escape(name_converter.convert(paper["first author"]))
            + '"})\n'
        )
        import_query += 'MERGE (person1)-[:相似 {命名: "中转英"}]->(people1)\n'
        import_query += 'MERGE (people1)-[:相似 {命名: "英转中"}]->(person1)\n'
        import_query += 'MERGE (person1)-[:发表 {角色: "主要作者"}]->(paper)\n'
        distint_id = 10
        for aff in paper.get("first author's affiliations") or []:
            import_query += (
                "MERGE (company"
                + str(distint_id)
                + ':公司 {名称: "'
                + _cy_escape(aff)
                + '"})\n'
            )
            import_query += (
                "MERGE (person1)-[:属于 {角色: \"归属单位\"}]->(company"
                + str(distint_id)
                + ")\n"
            )
            distint_id += 1
        co_authors = paper.get("co-first author") or []
        co_affs = paper.get("co-first author's affiliations") or []
        for idx, people in enumerate(co_authors):
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(people)
                + '"})\n'
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(name_converter.convert(people))
                + '"})\n'
            )
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ')-[:相似 {命名: "中转英"}]->(people'
                + str(distint_id)
                + ")\n"
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ')-[:相似 {命名: "英转中"}]->(person'
                + str(distint_id)
                + ")\n"
            )
            tmp_id = distint_id
            distint_id += 1
            import_query += (
                "MERGE (person"
                + str(tmp_id)
                + ')-[:发表 {角色: "其他作者"}]->(paper)\n'
            )
            if idx < len(co_affs):
                for aff in co_affs[idx] or []:
                    import_query += (
                        "MERGE (company"
                        + str(distint_id)
                        + ':公司 {名称: "'
                        + _cy_escape(aff)
                        + '"})\n'
                    )
                    import_query += (
                        "MERGE (person"
                        + str(tmp_id)
                        + ')-[:属于 {角色: \"归属单位\"}]->(company'
                        + str(distint_id)
                        + ")\n"
                    )
                    distint_id += 1
        import_query += (
            'SET paper.摘要 = "' + _cy_escape(paper.get("abstract", "")) + '"\n'
        )
        if paper.get("DOI"):
            import_query += 'SET paper.DOI = "' + _cy_escape(paper["DOI"]) + '"\n'
        if paper.get("ISSN"):
            import_query += 'SET paper.ISSN = "' + _cy_escape(paper["ISSN"]) + '"\n'
        if paper.get("publish time"):
            import_query += (
                'SET paper.出版日期 = "'
                + _cy_escape(paper["publish time"])
                + '"\n'
            )
        if paper.get("publisher"):
            import_query += (
                'SET paper.期刊 = "' + _cy_escape(paper["publisher"]) + '"\n'
            )
        if paper.get("关联依据"):
            import_query += (
                'SET paper.关联依据 = "'
                + _cy_escape(paper["关联依据"])
                + '"\n'
            )
        neo4j_graph.query(import_query)


def insert_patent_data(data: dict) -> None:
    for patent in data["patents"]:
        import_query = ""
        import_query += (
            'MERGE (patent:专利 {名称: "'
            + _cy_escape(patent["专利名称"])
            + '"})\n'
        )
        import_query += (
            'MERGE (person1:人员 {姓名: "'
            + _cy_escape(patent["第一发明人"])
            + '"})\n'
        )
        import_query += (
            'MERGE (people1:人员 {姓名: "'
            + _cy_escape(name_converter.convert(patent["第一发明人"]))
            + '"})\n'
        )
        import_query += 'MERGE (person1)-[:相似 {命名: "中转英"}]->(people1)\n'
        import_query += 'MERGE (people1)-[:相似 {命名: "英转中"}]->(person1)\n'
        import_query += 'MERGE (person1)-[:发表 {角色: "第一发明人"}]->(patent)\n'
        import_query += (
            'MERGE (company1:公司 {名称: "'
            + _cy_escape(patent["当前权利人"])
            + '"})\n'
        )
        import_query += (
            'MERGE (company2:公司 {名称: "'
            + _cy_escape(patent["申请人"])
            + '"})\n'
        )
        import_query += (
            'MERGE (place:地址 {名称:"'
            + _cy_escape(patent["申请人地址"])
            + '"})\n'
        )
        import_query += "MERGE (patent)-[:申请人地址]->(place)\n"
        import_query += "MERGE (patent)-[:当前权利人]->(company1)\n"
        import_query += "MERGE (patent)-[:申请人]->(company2)\n"
        distint_id = 10
        for people in patent.get("其他发明人") or []:
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(people)
                + '"})\n'
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ':人员 {姓名: "'
                + _cy_escape(name_converter.convert(people))
                + '"})\n'
            )
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ')-[:相似 {命名: "中转英"}]->(people'
                + str(distint_id)
                + ")\n"
            )
            import_query += (
                "MERGE (people"
                + str(distint_id)
                + ')-[:相似 {命名: "英转中"}]->(person'
                + str(distint_id)
                + ")\n"
            )
            import_query += (
                "MERGE (person"
                + str(distint_id)
                + ')-[:发表 {角色: "其他发明人"}]->(patent)\n'
            )
            distint_id += 1
        import_query += (
            'SET patent.摘要 = "' + _cy_escape(patent.get("摘要", "")) + '"\n'
        )
        import_query += (
            'SET patent.主权利要求 = "'
            + _cy_escape(patent.get("主权利要求", ""))
            + '"\n'
        )
        if patent.get("公开号"):
            import_query += (
                'SET patent.公开号 = "' + _cy_escape(patent["公开号"]) + '"\n'
            )
        if patent.get("申请号"):
            import_query += (
                'SET patent.申请号 = "' + _cy_escape(patent["申请号"]) + '"\n'
            )
        if patent.get("法律状态"):
            import_query += (
                'SET patent.法律状态 = "' + _cy_escape(patent["法律状态"]) + '"\n'
            )
        if patent.get("关联依据"):
            import_query += (
                'SET patent.关联依据 = "'
                + _cy_escape(patent["关联依据"])
                + '"\n'
            )
        if patent.get("专利类型"):
            import_query += (
                'SET patent.专利类型 = "'
                + _cy_escape(patent["专利类型"])
                + '"\n'
            )
        if patent.get("申请日期"):
            import_query += (
                'SET patent.申请日期 = "'
                + _cy_escape(patent["申请日期"])
                + '"\n'
            )
        if patent.get("公开日期"):
            import_query += (
                'SET patent.公开日期 = "'
                + _cy_escape(patent["公开日期"])
                + '"\n'
            )
        neo4j_graph.query(import_query)


def insert_expert_data(data: dict) -> None:
    core_name = (data.get("核心学者姓名") or "刘昌胜").strip()
    experts = data.get("experts", [])
    for ex in experts:
        name = (ex.get("姓名") or "").strip()
        if not name:
            continue
        py = name_converter.convert(name)
        topics = ex.get("研究方向")
        if isinstance(topics, list):
            topics = ";".join(topics)
        titles = ex.get("头衔")
        if isinstance(titles, list):
            titles = ";".join(titles)
        is_core = bool(ex.get("核心学者"))
        rel_summary = ex.get("与核心关系") or ""
        neo4j_graph.query(
            """
            MERGE (p:人员 {姓名: $name})
            MERGE (e:人员 {姓名: $py})
            MERGE (p)-[:相似 {命名: '中转英'}]->(e)
            MERGE (e)-[:相似 {命名: '英转中'}]->(p)
            SET p.英文名 = $en,
                p.单位 = $affil,
                p.关联依据 = $reason,
                p.H指数 = $h,
                p.总引用 = $tc,
                p.实验室 = $lab,
                p.职务 = $job,
                p.研究方向 = $topics,
                p.头衔 = $titles,
                p.邮箱 = $em,
                p.电话 = $ph,
                p.核心学者 = $is_core,
                p.与核心关系摘要 = $rel_summary
            """,
            {
                "name": name,
                "py": py,
                "en": ex.get("英文名") or "",
                "affil": ex.get("单位") or "",
                "reason": ex.get("关联依据") or "",
                "h": str(ex.get("H指数", "") or ""),
                "tc": str(ex.get("总引用", "") or ""),
                "lab": ex.get("实验室") or "",
                "job": ex.get("职务") or "",
                "topics": topics or "",
                "titles": titles or "",
                "em": ex.get("邮箱") or "",
                "ph": ex.get("电话") or "",
                "is_core": is_core,
                "rel_summary": rel_summary,
            },
        )
    for ex in experts:
        name = (ex.get("姓名") or "").strip()
        if not name or name == core_name:
            continue
        rel_summary = (ex.get("与核心关系") or "").strip()
        if not rel_summary:
            continue
        neo4j_graph.query(
            """
            MATCH (core:人员 {姓名: $core})
            MATCH (p:人员 {姓名: $name})
            MERGE (p)-[r:关联核心学者]->(core)
            SET r.说明 = $rel
            """,
            {"core": core_name, "name": name, "rel": rel_summary},
        )


def insert_competition_data(data: dict) -> None:
    teams = data.get("teams") or []
    topic = data.get("对比主题") or ""
    dims = data.get("分析维度")
    dims_str = "|".join(dims) if isinstance(dims, list) else ""
    for team in teams:
        partners = team.get("转化合作方") or []
        partner_str = "|".join(partners) if isinstance(partners, list) else str(partners)
        neo4j_graph.query(
            """
            MERGE (t:团队 {团队标识: $tid})
            SET t.团队名称 = $tname,
                t.机构简称 = $abbr,
                t.机构全称 = $fullorg,
                t.核心技术路线_标题 = $ct,
                t.核心技术路线_描述 = $cd,
                t.产品成熟度 = $mat,
                t.转化合作方 = $cp,
                t.AI洞察 = $ai,
                t.对比主题 = $topic,
                t.分析维度 = $dims
            """,
            {
                "tid": team.get("团队标识", ""),
                "tname": team.get("团队名称", ""),
                "abbr": team.get("机构简称", ""),
                "fullorg": team.get("机构全称", ""),
                "ct": team.get("核心技术路线_标题", ""),
                "cd": team.get("核心技术路线_描述", ""),
                "mat": team.get("产品成熟度", ""),
                "cp": partner_str,
                "ai": team.get("AI洞察", ""),
                "topic": topic,
                "dims": dims_str,
            },
        )
    if len(teams) >= 2:
        neo4j_graph.query(
            """
            MATCH (a:团队 {团队标识: $a}), (b:团队 {团队标识: $b})
            MERGE (a)-[r:竞品对照]->(b)
            SET r.主题 = $topic
            """,
            {
                "a": teams[0].get("团队标识", ""),
                "b": teams[1].get("团队标识", ""),
                "topic": topic,
            },
        )
    for team in teams:
        tid = team.get("团队标识", "")
        for pname in team.get("转化合作方") or []:
            neo4j_graph.query(
                """
                MATCH (t:团队 {团队标识: $tid})
                MERGE (c:公司 {名称: $p})
                MERGE (t)-[:转化合作方]->(c)
                """,
                {"tid": tid, "p": pname},
            )


_KIND_MERGE = {
    "scholar": ("人员", "姓名"),
    "org": ("机构", "名称"),
    "company": ("公司", "名称"),
    "patent_group": ("专利集合", "名称"),
    "topic": ("课题", "名称"),
}


def insert_scholar_kg_data(data: dict) -> None:
    for n in data.get("graph_nodes", []):
        kind = n.get("kind")
        name = n.get("name")
        if not kind or not name or kind not in _KIND_MERGE:
            continue
        label, prop = _KIND_MERGE[kind]
        neo4j_graph.query(
            f"MERGE (x:{label} {{{prop}: $name}})",
            {"name": name},
        )
    for lk in data.get("graph_links", []):
        sk = lk.get("source_kind")
        tk = lk.get("target_kind")
        if sk not in _KIND_MERGE or tk not in _KIND_MERGE:
            continue
        sl, sp = _KIND_MERGE[sk]
        tl, tp = _KIND_MERGE[tk]
        neo4j_graph.query(
            f"""
            MATCH (a:{sl} {{{sp}: $s}})
            MATCH (b:{tl} {{{tp}: $t}})
            MERGE (a)-[r:关联]->(b)
            SET r.类型 = $rel
            """,
            {"s": lk["source"], "t": lk["target"], "rel": lk.get("relation", "")},
        )
    center = data.get("center_scholar") or ""
    for m in data.get("milestones", []):
        neo4j_graph.query(
            """
            MATCH (p:人员 {姓名: $c})
            MERGE (ms:里程碑 {学者: $c, 年份: $y})
            SET ms.事件 = $evt
            MERGE (p)-[:经历]->(ms)
            """,
            {"c": center, "y": m.get("年份", ""), "evt": m.get("事件", "")},
        )


def insert_paper2author_data(data: dict) -> None:
    for edge in data.get("edges", []):
        title = edge.get("论文名称") or ""
        author = edge.get("作者姓名") or ""
        role = edge.get("角色") or "作者"
        if not title or not author:
            continue
        py = name_converter.convert(author)
        neo4j_graph.query(
            """
            MERGE (paper:论文 {名称: $title})
            MERGE (p:人员 {姓名: $author})
            MERGE (e:人员 {姓名: $py})
            MERGE (p)-[:相似 {命名: '中转英'}]->(e)
            MERGE (e)-[:相似 {命名: '英转中'}]->(p)
            MERGE (p)-[r:著作贡献 {角色: $role}]->(paper)
            """,
            {"title": title, "author": author, "py": py, "role": role},
        )


def get_tag() -> str:
    return st.text_input(
        "导入标签: company | product | paper | patent | expert | "
        "competition | scholar_kg | paper2author | all（从 data 目录批量导入）",
        value="all",
    )


def get_files():
    return st.file_uploader("上传 JSON（选择 all 时可不上传）")


def render_page():
    datamodel_image = Image.open("./images/datamodel.png")
    st.header("Zhiku Loader")
    st.subheader("将智库数据写入 Neo4j")
    st.caption("浏览器访问 http://localhost:7474/ 查看图数据。")

    user_input = get_tag()
    uploaded_file = get_files()

    if st.button("Import", type="primary"):
        with st.spinner("Loading... This might take a minute or two."):
            try:
                tag = (user_input or "").strip().lower()
                if tag == "all":
                    load_all_browse_data()
                else:
                    if uploaded_file is None:
                        st.error("请先上传 JSON 文件，或将标签设为 all。")
                        return
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
