from scripts.managedServicesActivator.merakiServices.merakidashboard import (
    MerakiDashboard,
)
from scripts.common_plan import CommonPlan
import json
import time


class Activate(CommonPlan):
    def process(self):
        """
        creates templates for mne organization
        also creates the organization if it does not already exist
        """
        # ------------- resource overhead
        self.logger.info(f"properties: {json.dumps(self.properties, indent=4)}")
        default_data_resource = self.get_resources_by_type_and_label(
            "charter.resourceTypes.MNEData",
            "default",
            no_fail=True
        )[0]["id"]
        defaults = self.bpo.resources.get(
            default_data_resource,
            obfuscate=False
        )
        self.api = defaults["properties"]["apiKey"]
        self.meraki = MerakiDashboard(
            self.api,
            self.logger,
            self.exit_error,
            self.bpo,
            self.resource["id"],
        )
        self.meraki.record_to_resource = True
        self.meraki.ignore_warnings = False

        default_orgs = self.meraki.get_template_and_inventory_orgs(defaults)
        self.template_org_id = default_orgs["template"]
        self.inventory_org_id = default_orgs["inventory"]

        # ------------- org
        # get the id from the payload
        self.org_id = self.properties.get("orgID", None)
        self.org_name = self.properties.get("orgName", "")
        self.template_name = self.properties.get("template_name", "default_template")

        new_org = False
        if not self.org_id:
            self.logger.info("Org id was not in payload")
            self.org_id = self.meraki.getOrganizationId(
                organizationName=self.org_name
            )
        if not self.org_id:
            self.logger.info("Org was not found by name, creating it from the template clone")
            new_org = True
            self.org_id = self.meraki.cloneOrganization(
                self.template_org_id, self.org_name
            )
            self.bpo.resources.patch_observed(
                self.resource["id"],
                {
                    "properties": {
                        "orgID": self.org_id
                    }
                },
            )
            time.sleep(5)

        # ------------- template
        template_id = ""
        if not new_org:
            # see if a template with the name exists if this was an org that was found, not newly created
            existing_templates = self.meraki.get_org_templates(self.org_id)
            for et in existing_templates:
                if et["name"] == self.template_name:
                    template_id = et["id"]
                    break

        if not template_id:
            # create the new template
            template_data = {
                "name": self.template_name
            }
            new_template = self.meraki.create_org_template(
                orgid=self.org_id,
                template_data=template_data
            )
            if new_template:
                template_id = new_template["id"]

        if template_id:
            self.bpo.resources.patch_observed(
                self.resource["id"],
                {
                    "properties": {
                        "template_id": template_id
                    }
                },
            )
            self.meraki.finish()
        else:
            self.meraki.log_issue(
                external_message="Failed to create organization template",
                internal_message="Failed to create organization template",
                api_response="",
                code=3010,
                details="",
                category=1
            )


class Terminate(Activate):
    def process(self):
        return
