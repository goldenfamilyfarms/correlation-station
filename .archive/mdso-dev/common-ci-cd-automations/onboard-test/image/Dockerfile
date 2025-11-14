FROM  registry.blueplanet.com/blueplanet/release/bpocore-dev:3.5.1-11470-74d9274

ARG GITLAB_TOKEN

# Prep for bpcore-cli + onboarding
RUN pip3 config unset --global global.index-url \
    && pip3 install --extra-index-url https://__token__:$GITLAB_TOKEN@git.blueplanet.com/api/v4/projects/3744/packages/pypi/simple bpocore-cli==0.0.57 \
    && ssh-keygen -q -N "" -f  ~/.ssh/id_rsa \
    && git config --global user.email "test@blueplanet.com" \
    && git config --global user.name "Tester" \
    && mkdir -p ~/.blueplanet/sites \
    && echo 'auth_scheme: no-auth \n\
base_url: http://localhost:8181 \n\
verify_certificate: False' \
    >> ~/.blueplanet/sites/default.yaml
