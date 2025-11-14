FROM golang:buster AS build-env
RUN apt install git
RUN go get github.com/jgroom33/blueplanet-screencapture
RUN cd /go/src/github.com/jgroom33/blueplanet-screencapture && go build -o screencapture

FROM python:3.8-buster

RUN apt update && apt install -y sshpass
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install -y ./google-chrome-stable_current_amd64.deb
WORKDIR /usr/local/src
COPY . .
COPY --from=build-env /go/src/github.com/jgroom33/blueplanet-screencapture/screencapture /usr/local/src

RUN pip3 install -r requirements.txt
RUN ansible-galaxy install -r requirements.yml

RUN echo 'export ANSIBLE_CONFIG=/usr/local/src/ansible.cfg' >> ~/.bashrc
