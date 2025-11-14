FROM  python:3.8-slim

WORKDIR /usr/local/src

ARG DOCKER_REGISTRY_USER
ARG DOCKER_REGISTRY_PASSWORD
ARG GITLAB_TOKEN
ARG PUSHER_HOST_PW

ENV GITLAB_TOKEN=$GITLAB_TOKEN
ENV DOCKER_REGISTRY_USER=$DOCKER_REGISTRY_USER
ENV DOCKER_REGISTRY_PASSWORD=$DOCKER_REGISTRY_PASSWORD
ENV SSHPASS=$PUSHER_HOST_PW

RUN apt-get update \
 && apt-get install -y --no-install-recommends git jq openssh-client sshpass \
 && apt-get purge -y --auto-remove \
 && rm -rf /var/lib/apt/lists/*

COPY misc/image  /usr/local/src/

# Python Dependencies
RUN pip3 install -r /usr/local/src/requirements-py3.txt

# Copy Build Scripts, Templates, & Tools
COPY scripts /usr/local/bin