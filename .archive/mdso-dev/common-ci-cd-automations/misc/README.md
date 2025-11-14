# Miscellaneous Jobs

A collection of misc jobs including:

- [Miscellaneous Jobs](#miscellaneous-jobs)
  - [Solution Deploy](#solution-deploy)
    - [Setup](#setup)
    - [Multiple MDSO Support](#multiple-mdso-support)
    - [Current Limitations/Future Improvements](#current-limitationsfuture-improvements)
  - [Copy-to-Registry - Your solution](#copy-to-registry---your-solution)
    - [Limitations](#limitations)
  - [Copy-to-Registry - Any solution](#copy-to-registry---any-solution)
    - [Usage](#usage)
    - [Limitations](#limitations-1)
  - [Copy-to-Registry MR solutions](#copy-to-registry-mr-solutions)
    - [Usage](#usage-1)
    - [Limitations](#limitations-2)
  - [Did-push](#did-push)
    - [Setup](#setup-1)
  - [Sphinx Doc Jobs](#sphinx-doc-jobs)
    - [Setup instructions](#setup-instructions)
      - [Setup gitlab-ci](#setup-gitlab-ci)
      - [Update setup.cfg](#update-setupcfg)
      - [Add documentation](#add-documentation)
      - [Setting requirements](#setting-requirements)
      - [Add project variables](#add-project-variables)
  - [Push to DevOpsExchange jobs](#push-to-devopsexchange-jobs)
  - [Publish Gitlab Pages](#publish-gitlab-pages)

## Solution Deploy

A manual job where:

1. Existing solution (if it exits) with the matching name will be undeployed with `--purge-host-vols`
2. New solution with the specified version will be deployed on the server

Each job will require you to set a `SOLUTION` variable. This must be the full solution name (eg `artifactory.ciena.com.blueplanet.bpo_ext:4.0.0`)


Note: It takes a sec before the job starts when you click the job trigger button. Don't press a 100 times

### Setup

To use this, you must:

- Install & register [shell runner](https://docs.gitlab.com/runner/executors/shell.html) on the target BP server with the tag `deploy`
  - [Install](https://docs.gitlab.com/runner/install/linux-manually.html) runner (use the `deb/gitlab-runner_amd64.deb` version)
  - Grab the runner token for your project/group under `Settings > CI/CD > Runners`
  - Register by running `gitlab-runner register`. Example here:

    ```
    root@ip-10-107-8-101:/home/bpadmin# gitlab-runner register
    Runtime platform                                    arch=amd64 os=linux pid=16919 revision=738bbe5a version=13.3.1
    Running in system-mode.

    Please enter the gitlab-ci coordinator URL (e.g. https://gitlab.com/):
    https://git.blueplanet.com/
    Please enter the gitlab-ci token for this runner:
    <GET YOUR OWN TOKEN FOR YOUR GROUP/PROJECT>
    Please enter the gitlab-ci description for this runner:
    <NAME>
    Please enter the gitlab-ci tags for this runner (comma separated):
    deploy
    Registering runner... succeeded                     runner=4ezgcrJ9
    Please enter the executor: docker-ssh, parallels, shell, virtualbox, kubernetes, custom, docker, ssh, docker+machine, docker-ssh+machine:
    shell
    Runner registered successfully. Feel free to start it, but if it's running already the config should be automatically reloaded!
    ```

- Add the following to your project's `.gitlab-ci.yml`:

    ```yaml
    include:
      - project: "BluePlanet/DevTools/common-ci-cd-automations"
        file: '/misc/.solution-deploy.yml'

    this-solution-deploy:
      extends: .this-solution-deploy
    ```

    > if you want your project to deploy any solution (including those outside of your solution project), use this instead:
      ```yaml
      include:
        - project: "BluePlanet/DevTools/common-ci-cd-automations"
          file: "/misc/.solution-deploy.yml"

      variables:
        SOLUTION: "thisisthenameofmysolution:1..3.4.4"

      solution-deploy:
        extends: .solution-deploy
      ```
- On the BP server, run the following as root:
  - `echo "gitlab-runner ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/gitlab_runner && usermod -aG docker gitlab-runner`

- On the BP server, install `jq` for the `solution_deploy` job to run correctly
  - `sudo apt update && sudo apt install jq -y`

### Multiple MDSO Support

If you wish to have multiple servers to push to, change the tags of each of those registered servers to something other than `deploy` and add in multiple jobs in you ci file. This way, you can select which server you'd like to deploy to by selecting the corresponding server. For example, you can have `deploy1`, `deploy2` runners with:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.solution-deploy.yml"

solution-deploy-server1:
  extends: .solution-deploy
  tags:
    - deploy1

solution-deploy-server2:
  extends: .solution-deploy
  tags:
    - deploy2
```

Update the tags according for any existing runners. This can be done in the UI under `Settings > CI/CD > Runners`

### Current Limitations/Future Improvements

- No orch redeploy supported. If DB needs to be purged, that must be done manually ahead of time

## Copy-to-Registry - Your solution

A manual job to copy solutions from artifactory to registry.bp.com. This is an automatic job by default to be used in the solution repo to run after the `build-solution` is complete.

Set a `DESTINATION` variable in your `.gitlab-ci.yml`. For example, if you want your solution to be available at `registry.blueplanet.com/blueplanet/registry/bpo-ext:4.0.0`, set `DESTINATION=blueplanet/registry`. This variable should be set in your project/group variable or your `.gitlab-ci.yml` file.

Add the following to your `.gitlab-ci.yml` file:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.copy-to-reg.yml"

variables:
  DESTINATION: registry.blueplanet.com/blueplanet/registry # change to your desired destination

copy-sol-to-reg:
  extends: .copy-sol-to-reg
```

### Limitations

* Please note that this job cannot be used in conjunction with the [copy-to-registry any solution job](#copy-to-registry---any-solution) in the same project.
* Only works from `artifactory.ciena.com/blueplanet` to any group in `registry.blueplanet.com`
* Must ensure the solution doesn't already exist in `registry.blueplanet.com`. Docker version on the pusher server is too old for `docker manifest`

## Copy-to-Registry - Any solution

Similar to [Copy-to-registry - your solution](#copy-to-registry---your-solution), but in this case, this job can be run for any solution. This is a manual job for any one off solutions that may not be currently available in registry.blueplanet.com.

### Usage

Along with the `DESTINATION` variable, you must set a `SOL_NAME` variable.

For example, if you want to push the solution `artifactory.ciena.com.blueplanet.bpo_ext:4.0.0`, set your `SOL_NAME=bpo_ext:4.0.0`

You can use a job variable while you kick off the job. However, there are a couple limitations:
* UI reaction is slow. You may be tempted to press `trigger` more than once
* retry doesn't allow you to set the variable

![Manual Job Example](manual_copy_any_to_reg.png)

Since retries don't work with manual job variables, it is recommended to add a variable `SOL_NAME` in your CI file instead. Every time you need to push a new solution, update the CI file, which will trigger the job.

Add the following to your `.gitlab-ci.yml` file:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.copy-to-reg.yml"

copy-any-to-reg:
    extends: .copy-any-to-reg
```

### Limitations

* Please note that this job cannot be used in conjunction with the [copy-to-registry your solution job](#copy-to-registry---your-solution) in the same project.
* Only works from `artifactory.ciena.com/blueplanet` to any group in `registry.blueplanet.com`
* Must ensure the solution doesn't already exist in `registry.blueplanet.com`. Docker version on the pusher server is too old for `docker manifest`

## Copy-to-Registry MR solutions

Similar to [Copy-to-registry - your solution](#copy-to-registry---your-solution), but in this case, this manual job can be run for any solution built for merge requests.

### Usage

Add the following to your `.gitlab-ci.yml` file:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.copy-to-reg.yml"

variables:
  DESTINATION: registry.blueplanet.com/blueplanet/bpcs/cust/<customer-xyz>/<release-registry-name>
  MAIN_BRANCH: master

copy-mr-sol-to-reg:
  extends: .copy-mr-sol-to-reg
```

### Limitations

* Please note that this job cannot be used in conjunction with the [copy-to-registry your solution job](#copy-to-registry---your-solution) in the same project.
* Only works from `artifactory.ciena.com/blueplanet` to any group in `registry.blueplanet.com`
* Must ensure the solution doesn't already exist in `registry.blueplanet.com`. Docker version on the pusher server is too old for `docker manifest`

## Did-push

A manual job to use did to push solution to a remote server. Target BP server must be accessible via ciena network but not accessible via artifactory (ie site-to-site tunnel)

The job will:

* Download every image in the solution
* did-save on runner
* did-push to target BP
* did-load on target BP
* solution_undeploy of any existing solution with a matching name
* solution_deploy new solution

### Setup

1. Setup your own docker runner (group runner recommended). *Do not use the shared ciena runner*
2. Generate SSH keys:
   1. Add public keys from your runner VM to the target's `authorized_keys`
   2. Add private keys in the group's CICD variable `SSH_PRIVATE_KEY`
3. Add the following in `.gitlab-ci.yaml` for each repo that you want to push to

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.did-push.yml"

did-push:
    extends: .did-push
    variables:
      USER: "root"
      DEST_BP: "10.10.10.10"
```


## Sphinx Doc Jobs

These jobs will allow you to build documentation using [sphinx](https://www.sphinx-doc.org/en/master/index.html) and publish docs to developer.blueplanet.com.

### Setup instructions

Refer to [planext as an example of a repo using these jobs](https://git.blueplanet.com/blueplanet/tools/public/bpo-tools/planext)

#### Setup gitlab-ci

Add this to your `.gitlab-ci.yaml` and update the `DOC_NAME` variable:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.sphinx-doc.yml"

build:doc:
  extends: .build:doc
push-doc:
  extends: .push-doc
  variables:
    DOC_NAME: "planext"
```

#### Update setup.cfg

In your `setup.cfg` add the following:

```ini
[build_sphinx]
source-dir = docs
build-dir = build
```

#### Add documentation

All documentation code should be added to `docs/` dir of the repository.
Refer to [planext as an example](https://git.blueplanet.com/blueplanet/tools/public/bpo-tools/planext)

#### Setting requirements

By default, the build job will only install the `sphinx` package. However, in many cases other packages, such as themes (furo, alabaster etc), or other packages imported in the python package that is being documented will be required. In that case, please include a `requirements_docs.txt` in your repo.

For example in [planext](https://git.blueplanet.com/blueplanet/tools/public/bpo-tools/planext/requirements_docs.txt) the following are required:

```
--extra-index-url https://artifactory.ciena.com/api/pypi/blueplanet-pypi/simple

sphinx
furo
plansdk
```

Note that sphinx requires dependent packages to be available to generate documentation. Since `planext` imports `plansdk`, `plansdk` must be included in the `requirements_docs.txt`

#### Add project variables

In order for the documentation to be made available on developer.blueplanet.com, the following 4 variables must be set in the project:

* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY
* DOCS_BUCKET_NAME
* DOCS_DISTRIBUTION_ID

## Push to DevOpsExchange jobs

> Refer [BP NFVO DOCS](https://git.blueplanet.com/blueplanet/blue-planet-product/bp-nfv-docs) and it's `.gitlab-ci.yml` file.

Include following in your `.gitlab-ci.yml` file, by filling `DOC_NAME` and `HTML_DOCS_PATH` folders:

```yaml
include:
  - project: "BluePlanet/DevTools/common-ci-cd-automations"
    file: "/misc/.push-to-devopsExchange.yml"

push-to-devOpsExchange:
  extends: .push-to-devOpsExchange
  variables:
    DOC_NAME: "YOUR_DOC_NAME"
    HTML_DOCS_PATH: "YOUR_HTML_FOLDER"
```

Following CI variables need to be defined under project's `Settings > CI/CD > Variables` section

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- DOCS_BUCKET_NAME
- PROD_DISTRIBUTION_ID

Please message `#gitlab-ci` on slack to have an admin configure these.

## Publish Gitlab Pages

> Refer [Core UI Developer Guide](https://git.blueplanet.com/blueplanet/blue-planet-product/core-ui-developer-guide) and it's `.gitlab-ci.yml` file.

Include following in your `.gitlab-ci.yml` file and assign the absolute path to the HTML folder of your docs project as a value to `HTML_DOCS_PATH` variable:

```yaml
include:
  - project: 'BluePlanet/DevTools/common-ci-cd-automations'
    file: '/misc/.gitlab-pages.yml'

stages:
  - deploy

variables: 
  HTML_DOCS_PATH: "YOUR_HTML_FOLDER"
```

For example, the value of `HTML_DOCS_PATH` can be `build/site/*`.

`Note:` Gitlab pages feature can be enabled under project's `Settings > General > Visibility` page.
