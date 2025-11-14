from beorn_app.dll.mdso import create_service, mdso_get, product_query


def create_managed_service(body):
    productId = product_query("ManagedServicesActivator")
    payload = {
        "label": body["fqdn"],
        "description": "FQDN",
        "productId": productId,
        "properties": {
            "fqdn": body["fqdn"],
            "operationType": "New",
            "model": body["model"],
            "ipAddress": body["ipAddress"],
            "configuration": body["configuration"],
            "vendor": body["vendor"],
            # 'firmwareVersion': body['firmwareVersion']
        },
        "autoclean": True,
    }
    return create_service(payload)


def get_existing_managed_service(fqdn):
    """
    Returns mdso managed services resource.

    Parameters:
        label (str): The label of the managed services resource. Typically FQDN.

    Returns:
        resource_id (str) : resource id of mdso managed services resource if it exists
        else, None will be returned.
    """

    endpoint = "/bpocore/market/api/v1/resources?resourceTypeId={}&q={}%3A{}&obfuscate=true&offset=0&limit=1".format(
        "charter.resourceTypes.ManagedServicesActivator", "properties.fqdn", fqdn
    )
    existing_resource = mdso_get(endpoint).get("items")
    if existing_resource and len(existing_resource) > 0:
        return existing_resource[0]
    else:
        return None
