query_dict = {
 "product2people": """
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{}\"
    MATCH (p)-[:属于]->(c:公司)
    OPTIONAL MATCH (z:专利)-[:申请人]->(c)
    OPTIONAL MATCH (p1:人员)-[r:发表]->(z)
    RETURN {{
        person : p1,
        relationship: r,
        patent: z}}
    LIMIT $limit
    """,
 "product2company": """
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{}\"
    MATCH (p)-[r1:属于]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r2:任职]->(c)
    OPTIONAL MATCH (c)-[r3:任职]->(c3:公司)
    RETURN {{
    patent: p,
    company: c,
    relationship1: r1,
    relationship2: r2,
    relationship3: r3,
    company2: c2,
    company3: c3
    }}
    LIMIT $limit
    """,
 "product2patent": """
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{}\"
    MATCH (p)-[:属于]->(c:公司)
    OPTIONAL MATCH (z:专利)-[:申请人]->(c)
    RETURN {{patent: z}}
    LIMIT $limit
    """,
 "product2paper": """
    MATCH (p:产品)
    WHERE p.名称 CONTAINS \"{}\"
    MATCH (p)-[:属于]->(c:公司)
    OPTIONAL MATCH (p1:人员)-[:任职]->(c)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:发表]->(pa:论文)
    RETURN {{
        person : person,
        relationship: r,
        paper: pa}}
    LIMIT $limit
    """,
 "company2product": """
    MATCH (c:公司)
    WHERE c.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:产品)-[r:属于]->(call)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(call)
    RETURN {{product: z, company: call, 
    relationship1: r1,
    relationship: r}}
    LIMIT $limit
    """,
 "company2people": """
    MATCH (c:公司)
    WHERE c.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:专利)-[:申请人]->(call)
    OPTIONAL MATCH (p1:人员)-[r:发表]->(z)
    RETURN {{
        person : p1,
        relationship: r,
        patent: z}}
    LIMIT $limit
    """,
 "company2patent": """
    MATCH (c:公司)
    WHERE c.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:专利)-[r:申请人]->(call)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(call)
    RETURN {{patent: z, company: call, 
    relationship1: r1,
    relationship: r
    }}
    LIMIT $limit
    """,
 "company2paper": """
    MATCH (c:公司)
    WHERE c.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (p1:人员)-[:任职]->(call)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:发表]->(pa:论文)
    RETURN {{
        person : person,
        relationship: r,
        paper: pa}}
    LIMIT $limit
    """,
 "people2product": """
    MATCH (p:人员)
    WHERE p.姓名 CONTAINS \"{}\"
    OPTIONAL MATCH (p2:人员)-[:相似]->(p)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:任职]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:产品)-[r:属于]->(call)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(call)
    RETURN {{product: z, company: call, 
    relationship1: r1,
    relationship: r}}
    LIMIT $limit
    """,
 "people2company": """
    MATCH (p:人员)
    WHERE p.姓名 CONTAINS \"{}\"
    OPTIONAL MATCH (p2:人员)-[:相似]->(p)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:任职]->(z:公司)
    RETURN {{people: person, company: z, 
    relationship: r
    }}
    LIMIT $limit
    """,
 "people2patent": """
    MATCH (p:人员)
    WHERE p.姓名 CONTAINS \"{}\"
    OPTIONAL MATCH (p2:人员)-[:相似]->(p)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:发表]->(z:专利)
    RETURN {{people: person, patent: z, 
    relationship: r
    }}
    LIMIT $limit
    """,
 "people2paper": """
    MATCH (p:人员)
    WHERE p.姓名 CONTAINS \"{}\"
    OPTIONAL MATCH (p2:人员)-[:相似]->(p)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:发表]->(pa:论文)
    RETURN {{
        person : person,
        relationship: r,
        paper: pa}}
    LIMIT $limit
    """,
"patent2product": """
    MATCH (p:专利)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p)-[r:申请人]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany, collect(r) + collect(r1) + collect(r2) as allr, p
    UNWIND allCompany as call
    OPTIONAL MATCH (z:产品)-[r3:属于]->(call)
    OPTIONAL MATCH (p)-[rr:申请人]->(call)
    RETURN {{product: z, company: call, patent:p,
    relationship1: allr,
    relationship: r3}}
    LIMIT $limit
    """,
"patent2people": """
    MATCH (p:专利)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p1:人员)-[r:发表]->(p)
    RETURN {{
        person : p1,
        relationship: {{
            type: type(r),
            properties: properties(r)
        }},
        patent: p}}
    LIMIT $limit
    """,
 "patent2company": """
    MATCH (p:专利)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p)-[r:申请人]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany, collect(r) + collect(r1) + collect(r2) as allr, p
    UNWIND allCompany as call
    UNWIND allr as rall
    RETURN {{patent: p, company: call, 
        relationship: allr
    }}
    LIMIT $limit
    """,
 "patent2paper": """
    MATCH (p:专利)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p)-[r:申请人]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany, collect(r) + collect(r1) + collect(r2) as allr, p
    UNWIND allCompany as call
    OPTIONAL MATCH (p1:人员)-[:任职]->(call)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    OPTIONAL MATCH (person)-[r:发表]->(pa:论文)
    RETURN {{
        person : person,
        relationship: r,
        paper: pa}}
    LIMIT $limit
    """,
 "paper2product": """
    MATCH (p:论文)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p1:人员)-[:发表]->(p)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    MATCH (person)-[r:任职]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:产品)-[r:属于]->(call)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(call)
    RETURN {{product: z, company: call, 
    relationship1: r1,
    relationship: r}}
    LIMIT $limit
    """,
"paper2company": """
    MATCH (p:论文)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p1:人员)-[:发表]->(p)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    MATCH (person)-[r:任职]->(c:公司)
    RETURN {{
        person : person,
        relationship: {{
            type: type(r),
            properties: properties(r)
        }},
        company: c}}
    LIMIT $limit
    """,
 "paper2patent": """
    MATCH (p:论文)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p1:人员)-[:发表]->(p)
    OPTIONAL MATCH (p2:人员)-[:相似]->(p1)
    OPTIONAL MATCH (p3:人员)-[:相似]->(:人员)-[:相似]->(p1)
    WITH collect(p2) + collect(p3) as allPeople
    UNWIND allPeople as person
    MATCH (person)-[r:任职]->(c:公司)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(c)
    OPTIONAL MATCH (c)-[r2:任职]->(c3)
    WITH collect(c) + collect(c2) + collect(c3) as allCompany
    UNWIND allCompany as call
    OPTIONAL MATCH (z:专利)-[r:申请人]->(call)
    OPTIONAL MATCH (c2:公司)-[r1:任职]->(call)
    RETURN {{patent: z, company: call, 
    relationship1: r1,
    relationship: r
    }}
    LIMIT $limit
    """,
"paper2people": """
    MATCH (p:论文)
    WHERE p.名称 CONTAINS \"{}\"
    OPTIONAL MATCH (p1:人员)-[r:发表]->(p)
    RETURN {{
        person : p1,
        relationship: {{
            type: type(r),
            properties: properties(r)
        }},
        patent: p}}
    LIMIT $limit
    """,


}