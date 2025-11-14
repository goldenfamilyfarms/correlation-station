Version 18.10.4
---------------
- Better logging when Mulesoft returns a 400 HTTP error.
- Set app name in onboard-helper.
- FIA IP update support.
- Network service deletion support.
- Fixed auto-creation of products during onboarding.

Version 18.10.2
---------------
- Removing unused methods in scriptplan.py
- Picking up onboard-helper for onboarding

Version 17.10.12
---------------
* DE-175
* More development of CPE activation

Version 17.10.11
---------------
* Fixed port activation bugs

Version 17.10.9
---------------
* Added RACutthroughTest
* Fixed self.log statements in CheckPortState
* Fixed unit tests
* Logging improvements in CommonPlan
* Don't treat "DHCP" like a hostname when used as CPE device_id

Version 17.10.9
---------------
* Avoid IP connectivity check to CPE if not using FQDN or static IP addr.

Version 17.10.8
---------------
* Fixed bug with apply groups

Version 17.10.7
---------------
* Many bug fixes including "big four".
* Added PortActivation resource type and service templates.
* Support FQDN

Version 17.10.6
---------------
* Changed circuit details source from Arda to new Mulesoft-hosted service. Large changes to circuit details model.
* Added support for FIA.
* Added support for ADVA 114 and 114Pro.
* Added support for PE-only, PE-CPE, PE-AGG, PE-AGG-MTU and PE-AGG-MTU-CPE spoke topologies.

Version 17.10.5
---------------
* Fixed rpconfig.yaml

Version 17.10.4
---------------
* Many changes in preparation for demo, driven by testing and Arda interface differences.

Version 17.10.3
---------------
* Many changes in preparation for demo.

Version 17.10.2
---------------
* Changed the service name.Solution deploy was failing, because it had _ in it.

Version 17.10.1
------------------
    Intital Version.
