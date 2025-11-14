# Quickstart templates

Quick start templates are canned ci templates with multiple jobs and stages included.

Certain tasks can be skipped by setting an ENV var in the project's settings

- [Available Quickstarts](#available-quickstarts)
- [Optional Jobs](#optional-jobs)
- [Notes](#notes)
  - [Skip specific tasks](#skip-specific-tasks)
  - [To add integration to your own channel](#to-add-integration-to-your-own-channel)
  - [BPI Quickstarts](#bpi-quickstarts)

## Available Quickstarts

| Template                                                            | [Lint](../lint/.lint-gitlab-ci-template-master.yml) | Test                                          | [Uprev](../auto-build/.auto-uprev-version.yml) | [App Img Build](../auto-build/.auto-build-app.yml) | Package                                                      | [Remote Solution Repo Uprev](../auto-build/.update-app-in-remote-fig-repo.yml) | [Solution Build](../auto-build/.auto-build-solution.yml) | [Did Artifact Build](../auto-build/.auto-build-solution-did.yml) | [Release App / solution](../auto-build/.auto-release.yml) |
| ------------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------- | ---------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------- |
| [app-py27](.quick-start-app-py27.yml)                               | :white_check_mark:                                  |                                               | :white_check_mark:                             | :white_check_mark:                                 |                                                              | :white_check_mark:                                                             |                                                          |                                                                  | :white_check_mark:                                        |
| [app-py3](.quick-start-app-py3.yml)                                 | :white_check_mark:                                  |                                               | :white_check_mark:                             | :white_check_mark:                                 |                                                              | :white_check_mark:                                                             |                                                          |                                                                  | :white_check_mark:                                        |
| [ra-py3](.quick-start-ra-py3.yml)                                   | :white_check_mark:                                  | [RA unittest](../ra-test/.ra-unittest-ps.yml) | :white_check_mark:                             | :white_check_mark:                                 |                                                              | :white_check_mark:                                                             |                                                          |                                                                  | :white_check_mark:                                        |
| [ra-py27](.quick-start-ra-py27.yml)                                 | :white_check_mark:                                  | [RA unittest](../ra-test/.ra-unittest-ps.yml) | :white_check_mark:                             | :white_check_mark:                                 |                                                              | :white_check_mark:                                                             |                                                          |                                                                  | :white_check_mark:                                        |
| [app-bpmn](.quick-start-app-bpmn.yml)                               | :white_check_mark:                                  |                                               | :white_check_mark:                             | :white_check_mark:                                 | [BPMN war](../bpmn/.mvn-package.yml)                         | :white_check_mark:                                                             |                                                          |                                                                  | :white_check_mark:                                        |
| [solo-ra-py3](.quick-start-solo-ra-py3.yml)                         | :white_check_mark:                                  | [RA unittest](../ra-test/.ra-unittest-ps.yml) | :white_check_mark:                             | :white_check_mark:                                 |                                                              |                                                                                | :white_check_mark:                                       | :white_check_mark:                                               | :white_check_mark:                                        |
| [solo-ra-py27](.quick-start-solo-ra-py27.yml)                       | :white_check_mark:                                  | [RA unittest](../ra-test/.ra-unittest-ps.yml) | :white_check_mark:                             | :white_check_mark:                                 |                                                              |                                                                                | :white_check_mark:                                       | :white_check_mark:                                               | :white_check_mark:                                        |
| [solution](.quick-start-solution.yml)                               |                                                     |                                               |                                                |                                                    |                                                              |                                                                                | :white_check_mark:                                       | :white_check_mark:                                               | :white_check_mark:                                        |
| [single-app-solution](.quick-start-single-app-solution.yml)         | :white_check_mark:                                  |                                               | :white_check_mark:                             | :white_check_mark:                                 |                                                              |                                                                                | :white_check_mark:                                       | :white_check_mark:                                               | :white_check_mark:                                        |
| [single-bpmnapp-solution](.quick-start-single-bpmnapp-solution.yml) | :white_check_mark:                                  |                                               | :white_check_mark:                             | :white_check_mark:                                 | [BPMN war](../bpmn/.mvn-package.yml)                         |                                                                                | :white_check_mark:                                       | :white_check_mark:                                               | :white_check_mark:                                        |
| [Python Package](.quick-start-python-package.yml)                   | :white_check_mark:                                  |                                               | :white_check_mark:                             |                                                    | [Python Package](../auto-build/.auto-build-pypi-package.yml) |                                                                                |                                                          |                                                                  |                                                           |
| [BPI-app](.quick-start-bpi-app.yml)                                 | code quality only                                   |                                               | future                                         | future                                             | [Jar/War](../auto-build/.auto-build-maven.yml)               | future                                                                         |                                                          |                                                                  | future                                                    |

<!--| [single-BPI-solution](.quick-start-single-bpi-solution.yml) | :white_check_mark:                            | :white_check_mark:                             | :white_check_mark:                                 | [BPI Jar/War](../auto-build/.auto-build-maven.yml)                 |                                                                                |                                                          | :white_check_mark:                                               | :white_check_mark:                                           | :white_check_mark: | -->

## Optional Jobs

These miscellaneous jobs are available in addition to the standard quickstart pipelines:

* [Onboard Test](../onboard-test/README.md) - Onboard resource Types to bpocore-dev
* [Mkpypi](../auto-build/.auto-build-pypi.yml) - Build a pypi image/solution using mkpypi
* [Solution Deploy](../misc/README.md#solution-deploy) - Deploy solution to server
* Copy to registry: Copy solution to registry.blueplanet.com from artifactory.ciena.com
  * [Copy-to-Registry - Your solution](../misc/README.md#copy-to-registry---your-solution)
  * [Copy-to-Registry - Any solution](../misc/README.md#copy-to-registry---any-solution)
* [Did-push](../misc/README.md#did-push) - Did-push solution to server
* [Sphinx Doc Jobs](../misc/README.md#sphinx-doc-jobs)

## Notes


### Skip specific tasks

* `uprev version.json` set SKIP_UPREV env var in project
* `release` set SKIP_RELEASE env var in project

### To add integration to your own channel

This will allow notifications to your project's channel when:

* new solution builds are available.
* new pypi build is available

1. Each slack channel you wish to add requires a new webhook to be added in the app. Please message #gitlab-ci on slack with your desired channel to get your group's channel added.
2. Once the webhook is added, you'd be provided the webhook URL. Take this, and add this to your solution repo's variables (`Settings > CI/CD > Variables`) called `CHANNEL_SLACK_WEBHOOK_URL`

![Variable](variables.png)


### BPI Quickstarts

To use the BPI quickstart, please contact @shapatel @wmohamma to get access to the required runner.

For each war/jar file that should be built in a BPI project, there needs to be a job created with the `PROJECT_PATH` defined.

For example:

```yaml
include:
  - project: 'BluePlanet/DevTools/common-ci-cd-automations'
    file: 'quick-start-templates/.quick-start-bpi-app.yml'

build:blueplanet-demo-rest:
  extends: .build-maven
  variables:
    PROJECT_PATH: "source_code/web/blueplanet-demo-rest"

build:blueplanet-demo-ui:
  extends: .build-maven
  variables:
    PROJECT_PATH: "source_code/web/blueplanet-demo-ui"
```

Set a project variable called `BPI_MAVEN_SETTINGS_XML` to be used as `settings.xml` during build jobs. 

*Note:* `BPI_MAVEN_SETTINGS_XML` is available as a group-level CI/CD variable under https://git.blueplanet.com/blueplanet/bpcs. All the projects created under this group will inherit it. 
