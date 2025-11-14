FROM python:3.8-slim

WORKDIR /usr/local/src
COPY lint/image  /usr/local/src/

RUN pip3 install -r requirements.txt \
    && apt-get update -qq && apt-get install -yqq curl \
    && curl -sL https://deb.nodesource.com/setup_9.x | bash \
    && apt-get install -yqq nodejs npm jq \
    && npm install jsonlint-tree -g \
    && apt-get purge -y --auto-remove \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

ARG GITLAB_TOKEN
ARG SLACK_WEBHOOK_URL
ENV GITLAB_TOKEN=$GITLAB_TOKEN
ENV SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL

COPY scripts /usr/local/bin

RUN echo "[global]\n" \
        "default = bp\n"    \
        "ssl_verify = true\n"   \
        "timeout = 5\n" \
        "[bp]\n"    \
        "url = https://git.blueplanet.com\n"    \
        "private_token = $GITLAB_TOKEN" >> /etc/python-gitlab.cfg
