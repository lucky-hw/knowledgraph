#!/bin/bash
# docker login --username=nick1687136441 crpi-ilpss0hdk02v3eun.cn-shanghai.personal.cr.aliyuncs.com

# Stop and remove existing container
docker kill zhiku-ai-service-test-loader-1 2>/dev/null || true
docker rm zhiku-ai-service-test-loader-1 2>/dev/null || true
docker kill zhiku-ai-service-test-bot-1 2>/dev/null || true
docker rm zzhiku-ai-service-test-bot-1 2>/dev/null || true
docker kill zhiku-ai-service-test-database-1 2>/dev/null || true
docker rm zhiku-ai-service-test-database-1 2>/dev/null || true

mkdir -p embedding_model
mkdir -p data
chown -R 7474:7474 data
chown -R 7474:7474 embedding_model
docker-compose down
docker compose up
