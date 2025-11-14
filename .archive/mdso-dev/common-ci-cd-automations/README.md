# Common CI-CD automations

Read this section from the handbook: https://git.blueplanet.com/blueplanet/bpcs/bestpractices/handbook/-/blob/master/testing/GitLab_automation/How-to-add-automation.md

Repo where all the common automation templates live.

Include templates in your `gitlab-ci.yml` file.

Supported CI templates (Not a current list):

|                                template                                 |                         description                          |                          Docker base                           |
| ----------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------- |
| [lint](lint/.lint-gitlab-ci-template.yml)                               | lint tosca, python, json                                     | [python:3](lint/image/Dockerfile)                              |
| [solution build](solution-build/.solution-build-gitlab-ci-template.yml) | build a solution from the repo's local solution/fig.j2 file  | [docker:latest](solution-build/image/Dockerfile)               |
| [solution build](auto-build/.auto-build-solution.yml)                   | build a solution from the common [fig.j2](auto-build/fig.j2) | docker:latest                                                  |
| [RA test](ra/ra-test/.ra-unittest-ci-template.yml)                      | run unit tests for an RA                                     | [base-image-devops-toolkit:20180223](ra-test/image/Dockerfile) |
| [RA build](ra/ra-build/.ra-build-ci-template.yml)                       | build/tag/push an RA                                         | [docker:latest](ra-build/image/Dockerfile)                     |
| [RA lint/build/test](auto-build/.auto-ra.yml)                           | complete RA CI with defaults                                 | several                                                        |

Each of the templates above use a custom Docker image that includes dependencies

## Usage

### Linting example

```yaml
include:
  - project: 'BluePlanet/DevTools/common-ci-cd-automations'
    file: '/lint/.lint-gitlab-ci-template.yml'
```

### RA Example

This will:

* lint
* unit tests
* image build (on all branches)   foo/`branch`/foo:0.0.1
* solution build (on all branches)  foo/`branch`/solution-foo:0.0.1
* create pdf from /docs
* create badge images from the contents of version.json

```yaml
include:
  - project: 'BluePlanet/DevTools/common-ci-cd-automations'
    file: '/auto-build/.auto-ra.yml'
```

## Using scripts

[Common scripts](scripts) are also included in each CI image.

## Environment Variables

Gitlab CI provides many standard [environment variables](https://docs.gitlab.com/ee/ci/variables/)

In addition, the common scripts set some environment variables for usage.  These are set during each CI stage execution in the CI image.

During a projects CI lifecycle, it is common to create a docker image.

Defaults:

|       ENV VAR       |                           example                           |                   default                   |
| ------------------- | ----------------------------------------------------------- | ------------------------------------------- |
| CI_REGISTRY_IMAGE   | registry.blueplanet.com/blueplanet/resourceadapters/bprafoo | registry.blueplanet.com/`path/to/your/repo` |
| NAME                | foora                                                       | extracted from version.json                 |
| VERSION             | 0.0.1                                                       | extracted from version.json                 |
| PROJECT_TAG         | 1                                                           | extracted from version.json                 |
| PROJECT_NEXT_TAG    | 2                                                           | calculated from version.json                |
| REGISTRY            | registry.blueplanet.com                                     | registry.blueplanet.com                     |
| CI_COMMIT_REF_NAME  | master                                                      | $CI_COMMIT_REF_NAME                         |
| VENDOR              | blueplanet/resourceadapters/bprafoo/master                  | `path/to/your/repo`/`branch`                |
| CI_COMMIT_SHORT_SHA | 2687ede5                                                    | $CI_COMMIT_SHORT_SHA                        |

### Recommended implementation

```yml
foo_task:
  before_script:
    - source commonci_set_env_vars
    - export IMAGE_TAG=$VERSION.$CI_COMMIT_SHORT_SHA
```

```yml
__version__: 1
solution_name: {{ NAME }}
solution_version: {{ IMAGE_VERSION }}
vendor: {{ VENDOR }}

apps:
    {{ NAME }}:
        image: {{ REGISTRY }}/{{ VENDOR }}/{{ NAME }}:{{ IMAGE_VERSION }}
        volumes:
           - /dev/log:/dev/log
```

## Examples

This project runs unit tests with .gitlab-ci.yml example files.

> Read through these for examples of how to include these common CI tasks in your project.

[solution build](test/solution_build/.gitlab-ci.yml)
[lint](test/lint/.gitlab-ci.yml)
[RA Test](test/ra/ra-test/.gitlab-ci.yml)
[RA Build](test/ra/ra-build/.gitlab-ci.yml)
