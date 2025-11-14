FROM python:3.8-buster

ARG PYPI='https://pypi.org/simple'
ARG PYPI_CREDS
ARG PIP_EXTRA_ARGS="--extra-index-url=https://$PYPI_CREDS@pypi.blueplanet.com/simple"

RUN apt update && apt install -y jq

WORKDIR /usr/local/src
COPY . .

RUN pip install -i $PYPI $PIP_EXTRA_ARGS -r requirements.txt
RUN cat /dev/zero | ssh-keygen -q -N ""
RUN git config --global user.email "dev@ciena.com"
RUN git config --global user.name "ST Onboarder"
