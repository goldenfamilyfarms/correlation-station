# Optional Testing Jobs

## Onboard Test

For testing resource type onboarding against `bpocore-dev`. Job will run on all commits pushed to merge requests + default branch.

To use, add the following to your `.gitlab-ci.yml`:

```yaml
include:
    - project: "BluePlanet/DevTools/common-ci-cd-automations"
        file: "/onboard-test/.onboard-test.yml"

onboard:test:
    extends: .onboard:test
```

:exclamation: **Note:**

* Only works where there are __no dependent resource types__
* [See which version of bpocore this test is run against](image/Dockerfile#L1).