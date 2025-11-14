# Required Setup

**Per group**

1. Generate a `ssh-keygen -t ed25519 -C <GROUP_NAME>` *Do not set a passphrase!*
2. Navigate to your repo's Settings > CI/CD > Environment variables
3. Add the following three variables:
	* SSH_PRIVATE_KEY: The private key that you generated in step 1. Include a new line at the end
	* DOCKER_REGISTRY_USER: If this is artifactory, you want to give it `bpplatlab1`
	* DOCKER_REGISTRY_PASSWORD: If this is artifactory, you want to give it `bpplatlab1`'s password

**Per repo**

1. For the first repo in your group, copy the public key and navigate to your repo's Settings > Repository > Deploy Keys
2. Give it a name (like `GroupA's deployment key`), then paste your key (everything in .ssh/<keyname>.pub) into the key field. Select 
`Write access allowed` and click submit
3. For all subsequent repos in your group, navigate to Settings > Repository > Deploy Keys and find the key you added in Step1 under 
`Privately accessible deploy keys`
4. Select `Enable`
5. Once that is enabled, go to `Enabled deploy keys` select `edit`
6. Enable `Write access allowed` and `Save changes`
7. Repeat for all repos that you want to enable auto-builds on in this group. 

## Version.json file

|   Property   |                Description                 |                                                                                                                         Sub properties                                                                                                                          | Optional |
| ------------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| name         | name of app or solution                    |                                                                                                                                                                                                                                                                 | No       |
| version      | version number (eg 18.10.1)                |                                                                                                                                                                                                                                                                 | No       |
| tag          | tag number                                 |                                                                                                                                                                                                                                                                 | Yes      |
| msdo_version | MSDO release version                       |                                                                                                                                                                                                                                                                 | Yes      |
| registry     | Docker registry (eg artifactory.ciena.com) |                                                                                                                                                                                                                                                                 | No       |
| vendor       | eg blueplanet                              |                                                                                                                                                                                                                                                                 | No       |
| pypi         | pypi properties                            | * version -> version of pypi image                                                                                                                                                                                                                              | Yes      |
| apps         | List of apps to include in solution        | * name <br> * version <br>* max_instances <br> * volumes <br> *  app_solution - if true, name & version of the app will be derived from the top level values <br> * pypi- if true, image with pypi version (if pypi.version is set) is included in the solution | No       |
| app_bar      | App bar options to include in solution fig |                                                                                                                                                                                                                                                                 | No       |

## Workflows

## For single app solution repo (with app + fig)

For single app solutions, you can make the field `"app_solution": true` in `version.json`. This will allow you to not have to set a `name` and 
`version` field under apps as it will be derived from the parent `name` and `version` fields. See example below:

```json
{
  "name": "bpo-ext",
  "version": "1.0.5",
  "tag": "22",
  "mdso_version": "18.10",
  "registry": "artifactory.ciena.com",
  "vendor": "blueplanet",
  "pypi": {
    "version": "3.6.0-1"
  },
  "apps": [
    {
      "app_solution": true,
      "volumes": [
        "/dev/log:/dev/log"
      ],
      "max_instances": "1"
    },
    {
      "pypi": true,
      "max_instances": "2"
    }
  ]
}
```

A typical use case will look like this:

1. Developer makes a change in a branch.
2. Change is merged into the `master` branch through a MR.
3. `uprev` job is triggered automatically. The tag value is updated in `version.json`
4. Both `build-app` and `build-solution` jobs is triggered automatically since `version.json` is updated. A docker image for the app as well as the
solution is created & pushed to the docker registry.

*When you're ready to release*

1. Once the app is ready to be released, the `release-app` pipeline is triggered manually. This increments the `version` field  and empties 
the `tag` field in `version.json`.  
2. Both `build-app` and `build-solution` jobs is triggered automatically since `version.json` is updated. A docker image for the app as well as the
solution is created & pushed to the docker registry.

## Separate APP and solution repo

A typical use case will look like this:

1. Developer makes a change in a branch. 
1. Change is merged into the `master` branch through a MR. 
1. `uprev` job is triggered automatically. The tag value is updated in `version.json`
1. `build-app` job is triggered automatically since `version.json` is updated. Docker image is built & pushed.
1. `update-app-in-solution` job is triggered automatically since `version.json` is updated. This triggers an update called `uprev-app` in the solution repo.
1. `uprev-app` job will update a specific app version and increment the solution tag.
1. `build-solution` job is triggered automatically since `version.json` is updated, and a solution is created & pushed to the docker registry.

*When you're ready to release*

1. Once the app is ready to be released, the `release` pipeline is triggered manually. This increments the `version` field  and empties the `tag` field in `version.json`.  
1. `build-app` job is triggered automatically since `version.json` is updated. Docker image is built & pushed.
1. `build-solution` job is triggered automatically since `version.json` is updated, and a solution is created & pushed to the docker registry.

## Possible Tweaks

* By default, only the `master` branch will trigger these builds. To add more branches add them like: 

```yaml
uprev-app:
  only:
    refs:
      - master
      - branch1
      - branch2

build-app:
  only:
    refs:
      - master
      - branch1
      - branch2
```

* The main branch is considered `master`. If you want to set a different branch for your main branch, add this to your CI file:

```yaml
variables:
  MAIN_BRANCH: "BRANCHX"
```
