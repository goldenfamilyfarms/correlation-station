# figmaker & get_image_tag

This library converts a version.json to a fig.yml with specified inputs

Use this in combination with [usolmaker](https://git.blueplanet.com/BluePlanet/DevTools/usolmaker/-/tree/master) to generate a solution image

```bash
pip install -i https://pypi.org/simple --extra-index-url https://$YOUR_GIT_BLUEPLANET_USERNAME:$YOUR_GIT_BLUEPLANET_PW@pypi.blueplanet.com/simple figmaker usolmaker
```

## figmaker Usage

usage: figmaker [-i INPUT] [-r REGISTRY] [-o OUTPUT] [-t TAG_TYPE] [--version]

`figmaker` converts a version.json into a fig.yml file

### TAG TYPE

The tag appended to the image and embedded in the fig.yml is determined by choosing a specific
precalculated tag_type.  The options are:

* semver:
    0.0.1
* semver_mdso:
    0.0.1.1902
* semver_mdso_sha:
    0.0.1.1902.ba878bb0
* semver_mdso_sha_pipelineiid:
    0.0.1.1902.ba878bb0.55
* semver_mdso_pipelineid_sha:
    0.0.1.1902.12345.ba878bb0

The PIPELINEIID and PIPELINEID is an environment variable from Gitlab CI.

### REGISTRY TYPE

* artifactory (artifactory.ciena.com)
* blueplanet (registry.blueplanet.com) are supported

When blueplanet is specified, the path (registry/vendor) to the image is calculated by using gitlab CI environment variables.

For local usage, the git remote origin is examined to determine the desired image path.

artifactory always uses blueplanet as a path (vendor)

### EXAMPLES

figmaker outputs the fig as a file or to stdout.

For example:

```bash
# generate a fig file compatible with pushing to artifactory for incremental dev releases
figmaker -r artifactory -t semver_mdso_sha_pipelineiid -o fig.yml
cat fig.yml
```

```bash
# generate a fig file compatible with pushing to artifactory for final release
figmaker -r artifactory -t semver_mdso -o fig.yml
cat fig.yml
```

## get_image_tag Usage

usage: get_image_tag [-i INPUT] [-t TAG_TYPE]

`get_image_tag` calculates the image tag.  This is helpful for `docker build` contexts

### TAG TYPE

The tag appended to the image and embedded in the fig.yml is determined by choosing a specific
precalculated tag_type.  The options are:

* semver:
    0.0.1
* semver_mdso:
    0.0.1.1902
* semver_mdso_sha:
    0.0.1.1902.ba878bb0
* semver_mdso_sha_pipelineiid:
    0.0.1.1902.ba878bb0.55
* semver_mdso_pipelineid_sha:
    0.0.1.1902.12345.ba878bb0

The PIPELINEIID and PIPELINEID is an environment variable from Gitlab CI.

## get_image_vendor Usage

usage: get_image_vendor [-r REGISTRY_TYPE]


### REGISTRY TYPE

* artifactory (artifactory.ciena.com)
* blueplanet (registry.blueplanet.com) are supported

When blueplanet is specified, the path (registry/vendor) to the image is calculated by using gitlab CI environment variables.

For local usage, the git remote origin is examined to determine the desired image path.

artifactory always uses blueplanet as a path (vendor)

optional arguments:

```
  -r REGISTRY    registry [artifactory or blueplanet] (default stdout)
  -i INPUT       path/to/version.json (default version.json)
  -o OUTPUT      Filename to write to (default stdout)
  -t TAG_TYPE    Image tag type to generate [semver, semver_mdso, semver_mdso_sha, semver_mdso_sha_pipelineiid]
  --version, -v  show program's version number and exit
```

## Contributing

[instructions](CONTRIBUTING.md)
