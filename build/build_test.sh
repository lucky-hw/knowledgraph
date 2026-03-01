#!/bin/bash

# Auto-increment version
VERSION_FILE="$(dirname "$0")/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0" > "$VERSION_FILE"
fi

OLD_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r MAJOR MINOR PATCH <<< "$OLD_VERSION"
OLD_VERSION_Loader="$MAJOR.$MINOR.$PATCH.1"
OLD_VERSION_Bot="$MAJOR.$MINOR.$PATCH.2"

PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "$NEW_VERSION" > "$VERSION_FILE"


NEW_VERSION_Database="$MAJOR.$MINOR.$PATCH.0"
NEW_VERSION_Loader="$MAJOR.$MINOR.$PATCH.1"
NEW_VERSION_Bot="$MAJOR.$MINOR.$PATCH.2"


cd "$(dirname "$0")/.."
REGISTRY="crpi-ilpss0hdk02v3eun.cn-shanghai.personal.cr.aliyuncs.com/linkingcare-wanghui"
REPO="zhiku-ai-service-test"  # Change this to your actual repo name
echo "Building version: $REGISTRY/$REPO:$NEW_VERSION"
# docker build -f ./Dockerfile -t $REGISTRY/$REPO:$NEW_VERSION .
docker pull --platform linux/amd64 neo4j:5
docker rmi  $REGISTRY/$REPO:$OLD_VERSION_Loader
docker rmi  $REGISTRY/$REPO:$OLD_VERSION_Bot
# 打标签并推送到阿里云
docker tag neo4j:5 $REGISTRY/$REPO:$NEW_VERSION_Database
docker buildx build --platform linux/amd64 -f ./loader.Dockerfile -t $REGISTRY/$REPO:$NEW_VERSION_Loader .
docker buildx build --platform linux/amd64 -f ./bot.Dockerfile -t $REGISTRY/$REPO:$NEW_VERSION_Bot .
#docker push $REGISTRY/$REPO:$NEW_VERSION_Database
docker push $REGISTRY/$REPO:$NEW_VERSION_Loader
docker push $REGISTRY/$REPO:$NEW_VERSION_Bot
