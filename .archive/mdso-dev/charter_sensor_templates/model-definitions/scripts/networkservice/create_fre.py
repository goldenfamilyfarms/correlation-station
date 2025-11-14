""" -*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of CreateFre plans

"""


class CreateFre:
    """this will create a TPE for the two devices links"""

    def __init__(self, common_plan):
        self.plan = common_plan

    def create_fre_by_id(self, a_port_id, z_port_id):
        """creates the FRE with the input of names"""
        a_tpe = self.plan.get_resource(a_port_id)
        z_tpe = self.plan.get_resource(z_port_id)
        return self.create_fre_by_resource(a_tpe, z_tpe)

    def create_fre_by_resource(self, a_tpe, z_tpe, circuit_details=None):
        """creates the FRE with the input of names"""
        label = a_tpe["label"] + "::" + z_tpe["label"]

        fre = {
            "orchState": "active",
            "properties": {
                "included": [
                    {
                        "relationships": {"tpes": {"data": [{"type": "tpes", "id": a_tpe["id"]}]}},
                        "attributes": {"role": "symmetrical", "directionality": "bidirectional"},
                        "type": "endPoints",
                        "id": "TPE1",
                    },
                    {
                        "relationships": {"tpes": {"data": [{"type": "tpes", "id": z_tpe["id"]}]}},
                        "attributes": {"role": "symmetrical", "directionality": "bidirectional"},
                        "type": "endPoints",
                        "id": "TPE2",
                    },
                ],
                "data": {
                    "relationships": {
                        "endPoints": {
                            "data": [{"type": "endPoints", "id": "TPE1"}, {"type": "endPoints", "id": "TPE2"}]
                        }
                    },
                    "attributes": {
                        "topologySources": ["stitched"],
                        "directionality": "bidirectional",
                        "networkRole": "FREAP",
                        "layerRate": "ETHERNET",
                        "active": True,
                        "nativeName": "",
                    },
                    "type": "fres",
                    "id": label,
                },
            },
            "label": "AUTO:" + label,
        }

        # Get the product
        product = self.plan.get_built_in_product(self.plan.BUILT_IN_FRE_TYPE)
        fre["productId"] = product["id"]
        self.plan.logger.info("FRE to add: " + str(fre))

        resource = self.plan.create_active_resource(
            "Waiting for " + label, None, fre, waittime=60, create_relationship=False
        ).resource
        self.plan.add_relationship("FRE/TPE", resource["id"], a_tpe["id"])
        self.plan.add_relationship("FRE/TPE", resource["id"], z_tpe["id"])
        if circuit_details:
            nw_service = self.plan.get_resource_by_type_and_properties(
                self.plan.BUILT_IN_NETWORK_SERVICE_TYPE,
                {"circuit_id": circuit_details["properties"]["circuit_id"]},
                no_fail=True,
            )
            self.plan.add_relationship("FRE/TPE", nw_service["id"], resource["id"])
