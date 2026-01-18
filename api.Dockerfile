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

COPY api.py .
COPY utils.py .
COPY chains.py .
COPY langgraph.json .
COPY search_prompt.yml .

HEALTHCHECK CMD curl --fail http://localhost:8504

ENTRYPOINT [ "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8504" ]
