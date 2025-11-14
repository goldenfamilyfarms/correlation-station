FROM docker:latest

WORKDIR /usr/local/src
COPY . .

RUN apk update \
 && apk add jq alpine-sdk python python-dev py-pip

# Pull common scripts
ARG CI_JOB_TOKEN
RUN git clone --depth 1 https://gitlab-ci-token:$CI_JOB_TOKEN@git.blueplanet.com/BluePlanet/DevTools/common-ci-cd-automations.git
RUN cp -r common-ci-cd-automations/scripts/* /usr/local/bin
