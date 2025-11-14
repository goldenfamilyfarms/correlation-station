FROM docker:latest

ARG PYPI='https://pypi.org/simple'
ARG PYPI_CREDS
ARG PIP_EXTRA_ARGS="--extra-index-url=https://$PYPI_CREDS@pypi.blueplanet.com/simple"
ARG CI_JOB_TOKEN

RUN apk update \
 && apk add jq alpine-sdk python python-dev py-pip

WORKDIR /usr/local/src
COPY . .

RUN pip install -i $PYPI $PIP_EXTRA_ARGS -r requirements.txt

# Pull common scripts
ARG CI_JOB_TOKEN
RUN git clone --depth 1 https://gitlab-ci-token:$CI_JOB_TOKEN@git.blueplanet.com/BluePlanet/DevTools/common-ci-cd-automations.git
RUN cp -r common-ci-cd-automations/scripts/* /usr/local/bin
