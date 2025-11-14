FROM  python:3.8

WORKDIR /usr/local/src

ARG DOCKER_REGISTRY_USER
ARG DOCKER_REGISTRY_PASSWORD
ARG GITLAB_TOKEN

ENV GITLAB_TOKEN=$GITLAB_TOKEN
ENV DOCKER_REGISTRY_USER=$DOCKER_REGISTRY_USER
ENV DOCKER_REGISTRY_PASSWORD=$DOCKER_REGISTRY_PASSWORD

ENV PYPI="https://artifactory.ciena.com/api/pypi/blueplanet-pypi/simple"

# Install External OS Dependencies
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common \
    # Install Docker
    && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
    && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    && apt-get update && apt-get install -y docker-ce-cli jq \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Internal OS Dependencies
RUN wget -O /usr/local/bin/mkpypi https://github.cyanoptics.com/Orchestrate/scriptplan/releases/download/mkpypi-1.1.4/mkpypi-1.1.4-linux-amd64 \
    && chmod +x /usr/local/bin/mkpypi \
    && wget $(wget -d -r -np  --spider -e robots=off --no-check-certificate https://github.cyanoptics.com/bp2/hostrepo/tree/master/xenial_extern 2>&1 | grep " -> " | grep -Ev "\/\?C=" | sed "s/.* -> //" | grep python-bp2hosttools | sed "s#blob#raw#") -O python-bp2hosttools.deb \
    && dpkg -i python-bp2hosttools.deb \
    && cp /usr/bin/python2.7 /opt/ciena/bp2hosttools/bin/ \
    && rm -rf github.cyanoptics.com

COPY auto-build/image  /usr/local/src/

# Python Dependencies
RUN  pip3 install -i $PYPI -r /usr/local/src/requirements-py3.txt

# Copy Build Scripts, Templates, & Tools
COPY auto-build/fig.j2 auto-build/images.j2 /usr/local/bin/
COPY scripts /usr/local/bin
