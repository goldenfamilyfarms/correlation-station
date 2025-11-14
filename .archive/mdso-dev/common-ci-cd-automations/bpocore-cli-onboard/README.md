# bpocore-cli Onboarder

This task uses bpocore cli to onboard ST's.  bpocore cli is included in the image `registry.blueplanet.com/BluePlanet/DevTools/common-ci-cd-automations/bpocore-cli-onboard:x.x.x`

## Usage

Three environment variables can be set in the ST repo:

* BPOCORE_BASE_URL (required)
* BPOCORE_USERNAME (optional. admin default)
* BPOCORE_PASSWORD (optional. bpadmin default)
* BPOCORE_ONBOARD_EXTRAS (optional. '' default)
  * i.e. use before_script to set `export BPOCORE_ONBOARD_EXTRAS="--auto-products"`

It is common for this onboarding task to be implemented as follows:

```
+--------------------------------------+
|   Customer Environment               |      +---------------------+
|                                      |      | git.blueplanet.com  |
|    +-------------------------+       |      |                     |
|    |  Gitlab Runner          |       |      |  +---------------+  |
|    |                   +------<---------<------< ST repository |  |
|    |  +----------------V---+ |       |      |  +---------------+  |
|    |  | solution onboarder >-->---+  |      |                     |
|    |  +--------------------+ |    |  |      +---------------------+
|    |                         |    +  |
|    +-------------------------+    V  |
|                                   +  |
|    +-------------------------+    |  |
|    |  MDSO Server            |    +  |
|    |                         |    V  |
|    |  +-----------+          |    +  |
|    |  | BP market +<--------<-----+  |
|    |  +-----------+          |       |
|    |                         |       |
|    +-------------------------+       |
|                                      |
+--------------------------------------+

```
