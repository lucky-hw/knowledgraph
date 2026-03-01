FROM langchain/langchain

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

RUN pip install --upgrade -r requirements.txt

COPY loader.py .
COPY utils.py .
COPY chains.py .
COPY neo4query.py .
COPY langgraph.json .
COPY search_prompt.yml .
COPY images ./images

EXPOSE 8502

HEALTHCHECK CMD curl --fail http://localhost:8502/_stcore/health

ENTRYPOINT ["streamlit", "run", "loader.py", "--server.port=8502", "--server.address=0.0.0.0"]
