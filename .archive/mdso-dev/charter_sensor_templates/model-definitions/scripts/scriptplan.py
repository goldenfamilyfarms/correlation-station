import json
import requests
import time
import collections
import logging
from plansdk.apis.plan import Plan


class Plan(Plan):
    market_path = "/bpocore/market/api/v1"
    ResourceInfo = collections.namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
    tron_path = "/tron/api/v1"
    all_profiles = None
    logger = logging.getLogger(__name__)

    def get_url(self, comp, path):
        """returns <Market URI>/comp/path

        Returns the URL String for the market API based on the path provided.

        :param comp: First part of the URL
        :param path: URL Path
        :type comp: str
        :type path: str
        :return: String the full http url
        :rtype: str

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> p.get_url('/bpocore/market/api/v1' '/resources')
        http://127.0.0.1:8181/bpocore/market/api/v1/resources
        """
        uri = self.params["uri"] + comp + path
        self.logger.info("URL: %s" % uri)
        return uri

    def tron_get(self, path):
        url = self.get_url(self.tron_path, path)
        self.logger.info("GET %s" % url)
        res = requests.get(url, verify=True, headers=self.bpo.transport.headers)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    # def tron_post(self, path, data=None):
    #     url = self.get_url(self.tron_path, path)
    #     self.log("POST %s %s" % (url, data))
    #     res = requests.post(url, data=data, headers=self.bpo.transport.headers,
    #                         verify=True)
    #     self.log("  %d" % (res.status_code, ))
    #     if res.status_code >= 300:
    #         self.log("  Error: %s" % res.text)
    #     return res

    # def tron_delete(self, path):
    #     url = self.get_url(self.tron_path, path)
    #     self.log("DELETE %s" % (url,))
    #     res = requests.delete(url, headers=self.bpo.transport.headers, verify=True)
    #     self.log("  %d" % (res.status_code, ))
    #     if res.status_code >= 300:
    #         self.log("  Error: %s" % res.text)
    #     return res

    # def tron_patch(self, path, data):
    #     url = self.get_url(self.tron_path, path)
    #     self.log("PATCH %s %s" % (url, data))
    #     res = requests.patch(url, data=json.dumps(data), headers=self.bpo.transport.headers,
    #                          verify=True)
    #     self.log("  %d" % (res.status_code, ))
    #     if res.status_code >= 300:
    #         self.log("  Error: %s" % res.text)
    #     return res

    def mget(self, path):
        """returns response from HTTP GET command

        This will return a response object from the GET request on the path.  The path does
        not include the IP/PORT, just the path.  The response object is from the python
        response.

        .. note::
             To get the information from the object use:
                * response.json() : Will return the objects
                * response.status_code(): Returns the HTTP Status Code
                * see: https://pypi.python.org/pypi/responses

        :param path: URL suffix path of the market (like /resources)
        :param verify_response: If True, will assert if the command is not successful (Default=False)
        :type comp: str
        :type verify_response: boolean
        :return: Response object
        :rtype: response

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> p.mget('/resources/123-123-123').status_code()
        200
        >>> p.mget('/resources/123-123-123').json()
        {u'orchState': u'active', u'_type': u'com.cyaninc.bp.market.Resource', u'desiredOrchState': u'active',
        u'resourceTypeId':
        u'ciscong.resourceTypes.L3VPN', u'tags': {u'service_discover': [u'true']},
        u'productId': u'589acaf3-86c0-499e-bd49-8ec326953212',
        u'differences': [{u'path': u'/properties/attachment/connection/routing-protocols/0/bgp/address-family',
        u'value': u'ipv4 unicast',
        u'op': u'replace'}, {u'path': u'/properties/service/svc-bandwidth', u'value': 181818, u'op': u'replace'}],
        u'autoClean': False,
        u'tenantId': u'07e4d137-7b97-4208-8a02-ccdf6d272258', u'discovered': False, u'reason': u'',
        u'providerData': {} }...
        """
        url = self.get_url(self.market_path, path)
        self.logger.info("GET %s" % url)
        res = requests.get(url, verify=True, headers=self.bpo.transport.headers)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code == 503:
            # Retry later
            self.logger.warning("Service is not able to handle request. Retry in 10 seconds.")
            time.sleep(10)
            res = requests.get(url, verify=True, headers=self.bpo.transport.headers)
            self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    def mpost(self, path, data=None):
        """performs a POST request, returns the resulting results object

        This will return a response object from the POST request on the path.  The path does
        not include the IP/PORT, just URI the path.  The response object is from the python
        response.

        .. note::
             To get the information from the object use:
                * response.json() : Will return the objects
                * response.status_code(): Returns the HTTP Status Code
                * see: https://pypi.python.org/pypi/responses

        :param path: URL suffix path of the market (like /resources)
        :param data: This can be a json format or dict object with the associated data to post.  If python dict it
                     will be coverted to a json string
        :param verify_response: If True, will assert if the command is not successful (Default=False)
        :type comp: str
        :type data: dict, str
        :type verify_response: boolean
        :return: Response object
        :rtype: response

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> res = p.mpost('/resources', data={u'orchState': u'active', u'_type': u'com.cyaninc.bp.market.Resource'...} )
        >>> res.status_code()
        200
        >>> res.json()
        {u'orchState': u'active', u'_type': u'com.cyaninc.bp.market.Resource', u'desiredOrchState': u'active',
        u'resourceTypeId':
        u'ciscong.resourceTypes.L3VPN', u'tags': {u'service_discover': [u'true']},
        u'productId': u'589acaf3-86c0-499e-bd49-8ec326953212',
        u'differences': [{u'path': u'/properties/attachment/connection/routing-protocols/0/bgp/address-family',
        u'value': u'ipv4 unicast',
        u'op': u'replace'}, {u'path': u'/properties/service/svc-bandwidth', u'value': 181818, u'op': u'replace'}],
        u'autoClean': False,
        u'tenantId': u'07e4d137-7b97-4208-8a02-ccdf6d272258', u'discovered': False, u'reason': u'',
        u'providerData': {} }...
        """
        url = self.get_url(self.market_path, path)
        self.logger.info("POST %s %s" % (url, data))
        res = requests.post(url, data=data, headers=self.bpo.transport.headers, verify=True)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    def mpatch(self, path, data):
        """performs a PATCH request, returns the resulting results object

        This will return a response object from the PATCH request on the path.  The path does
        not include the IP/PORT, just URI the path.  The response object is from the python
        response.

        .. note::
             To get the information from the object use:
                * response.json() : Will return the objects
                * response.status_code(): Returns the HTTP Status Code
                * see: https://pypi.python.org/pypi/responses

        :param path: URL suffix path of the market (like /resources)
        :param data: This can be a json format or dict object with the associated data to patch.  If python dict it
                     will be coverted to a json string
        :param verify_response: If True, will assert if the command is not successful (Default=False)
        :type comp: str
        :type data: dict, str
        :type verify_response: boolean
        :return: Response object
        :rtype: response

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> res = p.mpatch('/resources/123-123-123', data={u'orchState': u'active'} )
        >>> res.status_code()
        200
        >>> res.json()
        {u'orchState': u'active', u'_type': u'com.cyaninc.bp.market.Resource', u'desiredOrchState': u'active',
        u'resourceTypeId':
        u'ciscong.resourceTypes.L3VPN', u'tags': {u'service_discover': [u'true']}, u'productId':
        u'589acaf3-86c0-499e-bd49-8ec326953212',
        u'differences': [{u'path': u'/properties/attachment/connection/routing-protocols/0/bgp/address-family',
        u'value': u'ipv4 unicast',
        u'op': u'replace'}, {u'path': u'/properties/service/svc-bandwidth', u'value': 181818, u'op': u'replace'}],
        u'autoClean': False,
        u'tenantId': u'07e4d137-7b97-4208-8a02-ccdf6d272258', u'discovered': False, u'reason': u'',
        u'providerData': {} }...
        """
        url = self.get_url(self.market_path, path)
        self.logger.info("PATCH %s %s" % (url, data))
        res = requests.patch(url, data=json.dumps(data), headers=self.bpo.transport.headers, verify=True)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    def mput(self, path, data=None):
        """performs a PUT request, returns the resulting results object

        This will return a response object from the PUT request on the path.  The path does
        not include the IP/PORT, just URI the path.  The response object is from the python
        response.

        .. note::
             To get the information from the object use:
                * response.json() : Will return the objects
                * response.status_code(): Returns the HTTP Status Code
                * see: https://pypi.python.org/pypi/responses

        :param path: URL suffix path of the market (like /resources)
        :param data: This can be a json format or dict object with the associated data to put.  If python dict it
                     will be converted to a json string
        :param verify_response: If True, will assert if the command is not successful (Default=False)
        :type comp: str
        :type data: dict, str
        :type verify_response: boolean
        :return: Response object
        :rtype: response

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> res = p.mput('/resources/123-123-123', data={u'orchState': u'active', u'_type': u'c...'})
        >>> res.status_code()
        200
        >>> res.json()
        {u'orchState': u'active', u'_type': u'com.cyaninc.bp.market.Resource', u'desiredOrchState': u'active',
        u'resourceTypeId': u'ciscong.resourceTypes.L3VPN', u'tags': {u'service_discover': [u'true']},
        u'productId': u'589acaf3-86c0-499e-bd49-8ec326953212',
        u'differences': [{u'path': u'/properties/attachment/connection/routing-protocols/0/bgp/address-family',
        u'value': u'ipv4 unicast', u'op': u'replace'}, {u'path': u'/properties/service/svc-bandwidth',
        u'value': 181818, u'op': u'replace'}], u'autoClean': False,
        u'tenantId': u'07e4d137-7b97-4208-8a02-ccdf6d272258', u'discovered': False, u'reason': u'',
        u'providerData': {} }...
        """
        url = self.get_url(self.market_path, path)

        if isinstance(data, dict):
            data = json.dumps(data)
        self.logger.info("PUT %s %s" % (url, data))
        res = requests.put(url, data=data, headers=self.bpo.transport.headers, verify=True)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    def mdelete(self, path):
        """performs a DELETE request, returns the resulting results object

        This will return a response object from the DELETE request on the path.  The path does
        not include the IP/PORT, just URI the path.  The response object is from the python
        response.

        .. note::
             To get the information from the object use:
                * response.json() : Will return the objects
                * response.status_code(): Returns the HTTP Status Code
                * see: https://pypi.python.org/pypi/responses

        :param path: URL suffix path of the market (like /resources)
        :param verify_response: If True, will assert if the command is not successful (Default=False)
        :type comp: str
        :type verify_response: boolean
        :return: Response object
        :rtype: response

        :Example:

        >>> import Plan
        >>> p = Plan()
        >>> res = p.delete('/resources/123-123-123')
        >>> res.status_code()
        201
        """
        url = self.get_url(self.market_path, path)
        self.logger.info("DELETE %s" % (url,))
        res = requests.delete(url, headers=self.bpo.transport.headers, verify=True)
        self.logger.info("  %d" % (res.status_code,))
        if res.status_code >= 300:
            self.logger.info("  Error: %s" % res.text)
        return res

    # def get_tenant_id(self, tenant_name):
    #     res = self.tron_get('/tenants?name=%s' % tenant_name).json()
    #     uuid = res["results"][0]["uuid"]
    #     self.log("Tenant ID for %s is %s" % (tenant_name, uuid))
    #     return uuid

    # def create_tenant(self, parent_tenant_id, tenant_name):
    #     data = {
    #         "description": tenant_name,
    #         "displayName": tenant_name,
    #         "isActive": True,
    #         "name": tenant_name,
    #         "parent": parent_tenant_id,
    #     }
    #     self.tron_post('/tenants', json.dumps(data))
    #
    #     tenant_id = self.get_tenant_id(tenant_name)
    #
    #     data = {
    #         "isActive": True,
    #     }
    #     self.tron_patch('/tenants/%s' % tenant_id, data)

    # def deactivate_tenant(self, tenant_id):
    #     data = {
    #         "isActive": False,
    #     }
    #     self.tron_patch('/tenants/%s' % tenant_id, data)

    def get_dependencies(self, resource_id, resource_type=None, recursive=False, exception_on_failure=False):
        """return the list of dependencies

        Dependencies are resources that this resource depends upon.  A specific resource
        type can be passed in as a filter (optional).  If recursive is set to true
        it will walk the resource relationship tree to get all associated resources.

        :param resource_id: Id of the source resource
        :param resource_type: (Optional) Single resource type or List of resource types filter
        :param recursive: Perform a recursive search (Default is False)
        :param exception_on_failure: If the command should fail, return an exception
        :type resource_id: str
        :type resource_type: list/str
        :type recursive: boolean
        :type exception_on_failure: boolean

        :return: List of resource objects
        :rtype: list of dicts
        """
        returnValue = []
        resource_types = []
        if not isinstance(resource_type, list):
            if resource_type is None:
                url = "/resources/{}/dependencies?recursive={}&limit=2000".format(resource_id, recursive)
                self.logger.info("Stop calling dependencies function without a resource type")
            else:
                url = "/resources/{}/dependencies?recursive={}&resourceTypeId={}&limit=2000".format(
                    resource_id, recursive, resource_type
                )
                self.logger.info(url)
            reply = self.mget(url)
            if reply.status_code // 100 > 2:
                self.logger.warning(reply.status_code)
            elif reply.status_code < 220:
                returnValue = reply.json()["items"]
            elif exception_on_failure is True:
                raise Exception("Unable to get dependencies for resource id: " + resource_id)
        else:
            # Keeping this code for backward compatibility
            self.logger.info("Keeping Track if this is ever used")
            self.logger.info("This is serious trouble for memory")
            resource_types = resource_type

            url = "/resources/%s/dependents?recursive=%s&limit=2000" % (resource_id, str(recursive).lower())

            reply = self.mget(url)
            if reply.status_code < 220:
                dependencies = reply.json()
                self.logger.info(dependencies)
                for dep in dependencies["items"]:
                    if resource_type is None or dep["resourceTypeId"] in resource_types:
                        returnValue.append(dep)
            elif exception_on_failure is True:
                raise Exception("Unable to get dependencies for resource id: " + resource_id)

        self.logger.info("Returning %s dependencies." % str(len(returnValue)))
        return returnValue

    def get_dependents(self, resource_id, resource_type=None, recursive=False, exception_on_failure=False, await_active=False):
        """return the list of dependents

        Dependents are those resources that depend upon this resource.  A specific resource
        type can be passed in as a filter (optional).  If recursive is set to true
        it will walk the resource relationship tree to get all associated resources.

        :param resource_id: Id of the source resource
        :param resource_type: (Optional) Single resource type or List of resource types filter
        :param recursive: Perform a recursive search (Default is False)
        :param exception_on_failure: If the command should fail, return an exception
        :type resource_id: str
        :type resource_type: list/str
        :type recursive: boolean
        :type exception_on_failure: boolean

        :return: List of resource objects
        :rtype: list of dicts
        """

        returnValue = []
        resource_types = []
        if not isinstance(resource_type, list):
            if resource_type is None:
                url = "/resources/{}/dependents?recursive={}&limit=2000".format(resource_id, recursive)
                self.logger.warning("Stop calling dependents function without a resource type")
            else:
                url = "/resources/{}/dependents?recursive={}&resourceTypeId={}&limit=2000".format(
                    resource_id, recursive, resource_type
                )
            reply = self.mget(url)
            if reply.status_code < 220:
                returnValue = reply.json()["items"]
            elif exception_on_failure is True:
                raise Exception("Unable to get dependents for resource id: " + resource_id)
        else:
            # Keeping this code for backward compatibility
            self.logger.info("Keeping Track if this is ever used")
            self.logger.info("This is serious trouble for memory")
            resource_types = resource_type

            url = "/resources/%s/dependents?recursive=%s&limit=2000" % (resource_id, str(recursive).lower())

            reply = self.mget(url)
            if reply.status_code < 220:
                dependencies = reply.json()
            for dep in dependencies["items"]:
                if resource_type is None or dep["resourceTypeId"] in resource_types:
                    returnValue.append(dep)
                elif exception_on_failure is True:
                    raise Exception("Unable to get dependents for resource id: " + resource_id)
        if await_active and returnValue:
            self.await_active_collect_timing([returnValue[0]['id']], interval=1.0, tmax=300.0)

        self.logger.info("Returning %s dependents." % str(len(returnValue)))
        return returnValue

    # def get_dependents_by_type_and_partial_query(self, resource_id,
    #                                              resource_type, partial_query=None,
    #                                              recursive=False):
    #     '''return the list of dependents
    #
    #     Dependents are those resources that depend upon this resource.  A specific resource
    #     type can be passed in as a filter. A Partial Query is an optional parameter which can
    #      be passed to limit the numnber of responses.  If recursive is set to true
    #     it will walk the resource relationship tree to get all associated resources.
    #
    #     :param resource_id: Id of the source resource
    #     :param resource_type: (Optional) Single resource type or List of resource types filter
    #     :param recursive: Perform a recursive search (Default is False)
    #     :param partial_query: Partial_query to limit the responses
    #     :type resource_id: str
    #     :type resource_type: list/str
    #     :type recursive: boolean
    #     :type exception_on_failure: boolean
    #
    #     :return: List of resource objects
    #     :rtype: list of dicts
    #     '''
    #
    #     st = "/resources/%s/dependents?recursive=%s&resourceTypeId=%s" % \
    #       (resource_id, str(recursive).lower(), resource_type)
    #
    #     if partial_query is not None:
    #         st += "&p=%s" % partial_query
    #
    #     res = self.mget(st).json()
    #
    #     return res

    # def get_dependency_by_type_and_properties(self, resource_id, resource_type, props):
    #
    #     deps = self.get_dependencies_by_type(resource_id, resource_type)
    #
    #     matches = []
    #     for dep in deps:
    #         match = True
    #         for k, v in props.items():
    #             if dep["properties"].get(k) != v:
    #                 match = False
    #         if match:
    #             matches.append(dep)
    #
    #     assert len(matches) == 1, matches
    #     return list(matches)[0]

    # def get_dependencies_by_type_and_label(self, resource_id, resource_type, label):
    #
    #     res = self.mget('/resources/%s/dependencies?' % resource_id)
    #     deps = (dep for dep in res.json()["items"] if dep["resourceTypeId"] in [resource_type])
    #     return [dep for dep in deps if dep["label"] == label]

    def get_resource(self, resource_id):
        res = self.mget("/resources/%s" % resource_id).json()
        return res

    def get_observed(self, resource_id):
        res = self.mget("/resources/%s/observed" % resource_id).json()
        return res

    def patch_resource(self, resource_id, data):
        resp = self.mpatch("/resources/%s" % resource_id, data)
        assert resp.status_code < 210

    # def update_resource(self, resource_id, data):
    #     resp = self.mput("/resources/%s" % resource_id, data)
    #     assert resp.status_code < 210

    def patch_observed(self, resource_id, data):
        resp = self.mpatch("/resources/%s/observed" % resource_id, data)
        assert resp.status_code < 210

    def get_resource_by_type_and_properties(
        self, resource_type, props, domain_id=None, no_fail=False, return_all_matches=False
    ):
        st = "/resources?resourceTypeId=%s" % resource_type

        if domain_id:
            st += "&domainId=%s" % domain_id

        st += "&q="
        # for k, v in props.items():
        #     st += "properties.%s:%s," % (str(k), str(v))
        for k in props.keys():
            st += "properties.%s:%s," % (str(k), str(props[k]))

        res = self.mget(st).json()

        if return_all_matches:
            return res["items"]

        if len(res["items"]) != 1:
            if not no_fail:
                assert False, "Too many or few resources returned for %s, %s" % (props, res)
            return None
        else:
            return res["items"][0]

    def get_resource_by_type_and_label(self, resource_type, label, domain_id=None, no_fail=False, partial=False):
        st = "/resources?resourceTypeId=%s" % resource_type

        if domain_id:
            st += "&domainId=%s" % domain_id

        st += "&p=" + "label:%s" % label if partial else "&q=" + "label:%s" % label
        res = self.mget(st).json()

        if len(res["items"]) != 1:
            if not no_fail:
                assert False, "Too many or few resources returned for %s, %s" % (label, res)
            return None
        else:
            return res["items"][0]

    def get_resources_by_type_and_label(self, resource_type, label, domain_id=None, no_fail=False):
        st = "/resources?resourceTypeId=%s" % resource_type

        if domain_id:
            st += "&domainId=%s" % domain_id

        st += "&q=" + "label:%s" % label

        res = self.mget(st).json()
        if len(res["items"]) == 0:
            if not no_fail:
                assert False, "No matching resources found for %s, %s" % (label, res)
            return None
        else:
            return res["items"]

    def get_resources_by_type_and_properties(self, resource_type, props, domain_id=None):
        st = "/resources?resourceTypeId=%s" % resource_type

        if domain_id:
            st += "&domainId=%s" % domain_id

        st += "&q="

        try:
            for k, v in props.items():
                st += "properties.%s:%s," % (str(k), str(v))
        except Exception:
            for k, v in props.items():
                st += "properties.%s:%s," % (str(k), str(v))
        res = self.mget(st).json()
        return res["items"]

    def get_resources_by_type(self, resource_type):
        res = self.mget("/resources?resourceTypeId=%s" % (resource_type)).json()
        return res["items"]

    def get_resources_by_domain_type_and_label(self, domain_id, resource_type, label):
        res = self.mget(
            "/resources?obfuscate=false&domainId=%s&resourceTypeId=%s&q=label:%s" % (domain_id, resource_type, label)
        ).json()
        return res

    # def get_resource_by_label_and_type(
    #         self, resource_label, resource_type_uri, no_fail=False):
    #     self.log('find resource %s of type %s' % (resource_label,
    #                                               resource_type_uri))
    #     resources = [u for u in
    #                  self.mget("/resources?resourceTypeId=%s" %
    #                            resource_type_uri).json()["items"]
    #                  if u["label"] == resource_label]
    #     if len(resources) > 1:
    #         assert False, "Too many resources with label %s returned" % resource_label
    #     if len(resources) == 0:
    #         if no_fail:
    #             return None
    #         else:
    #             assert False, "No resources with label %s returned" % resource_label
    #     resource = resources[0]
    #     self.log("  Market ID: " + resource["id"])
    #     self.log("  Provider ID: " + resource["providerResourceId"])
    #     return resource

    def get_custom_operations(self, resource_id, state_filter=None):
        """return the list of customer operations against a resource id

        You can provide a state_filter to get the a specific operation based
        on its state (for instance those that are pending or running

        :param resource_id: Id of the source resource
        :param state_filter: (Optional) List of states
        :type resource_id: str
        :type state_filter: list/str

        :return: List of operation objects
        :rtype: list of dicts
        """
        returnValue = []
        state_filters = []
        if state_filter is None or isinstance(state_filter, str):
            state_filters.append(state_filter)
        else:
            state_filters = state_filter

        reply = self.mget("/resources/%s/operations" % resource_id)
        if reply.status_code < 220:
            operations = reply.json()
            self.logger.info(operations)
            for operation in operations["items"]:
                if state_filter is None or operation["state"] in state_filters:
                    returnValue.append(operations)

        self.logger.info("Returning %s custom operations." % str(len(returnValue)))
        return returnValue

    def get_products_by_type_and_domain(self, resource_type_uri, domain_id):
        if self.all_profiles is None:
            self.all_profiles = self.mget("/products?includeInactive=true").json()["items"]

        return [
            p for p in self.all_profiles if (p["resourceTypeId"] == resource_type_uri and p["domainId"] == domain_id)
        ]

    # def create_domain(self, title, domain_type, url, properties, tenant_id=None):
    #     self.log("Creating Domain %s" % title)
    #
    #     resp = self.mget('/resource-providers').json()['items']
    #     providers = [p for p in resp if p["domainType"] == domain_type]
    #     self.log(providers)
    #     assert len(providers) == 1
    #
    #     body = {
    #         "title": title,
    #         "domainType": domain_type,
    #         "accessUrl": url,
    #         "rpId": providers[0]["id"],
    #         "properties": properties,
    #     }
    #
    #     if tenant_id:
    #         body["tenantId"] = tenant_id
    #
    #     resp = self.add("Domain", "/domains", body)

    # def delete_domain(self, domain_id):
    #     self.log("Deleting domain for %s" % domain_id)
    #     self.mdelete('/domains/%s' % domain_id)

    # def get_domain_id(self, domain_type):
    #     domains = self.mget('/domains?q=domainType:%s' % domain_type).json()['items']
    #     assert len(domains) == 1, 'No domain or more than one domain found matching %s' % domain_type
    #     return domains[0]["id"]

    # def get_domain_by_type(self, domain_type, tenant_id=None, return_list=False):
    #     domains = self.mget('/domains?q=domainType:%s' % domain_type).json()['items']
    #     if tenant_id:
    #         domains = [d for d in domains if d['tenantId'] == tenant_id]
    #     if return_list:
    #         return domains
    #     else:
    #         assert len(domains) == 1, 'No domain or more than one domain found matching %s' % domain_type
    #         return domains[0]["id"]

    # def get_domain_by_type_and_url(self, domain_type, url, return_list=False):
    #     assert url.startswith('http')
    #     doms = self.mget('/domains?q=domainType:%s' % domain_type).json()['items']
    #     self.log('Looking for domain url %s in domains %s' % (url, doms))
    #     domains = [d for d in doms if d['accessUrl'].split(':')[1:-1] == url.split(':')[1:-1]]
    #     if return_list:
    #         return domains
    #     else:
    #         assert len(domains) == 1, 'No domain or more than one domain found matching %s' % domain_type
    #         return domains[0]["id"]

    # def get_product_ids_in_domain(self, domain_id):
    #     prods = self.mget('/products?includeInactive=true').json()['items']
    #     return dict([(p['resourceTypeId'], p['id'])
    #                  for p in prods if p['domainId'] == domain_id])

    # def get_product_map(self):
    #     prods = self.mget('/products?includeInactive=true').json()['items']
    #     # pprint.pprint(prods)
    #     return dict([(p['id'], p['domainId']) for p in prods])

    def get_resource_by_type_and_domain(self, type_uri, domain_id):
        things = self.mget("/resources?obfuscate=false&resourceTypeId=%s&domainId=%s" % (type_uri, domain_id)).json()["items"]
        self.logger.info("  found %d %s resources" % (len(things), type_uri.rpartition(".")[2]))
        return things

    def get_resource_by_provider_resource_id(self, domain_id, provider_resource_id, retries=1, no_fail=False):
        self.logger.info("find resource with provider id %s in domain %s" % (provider_resource_id, domain_id))
        for cnt in range(retries):
            cnt = cnt
            reply = self.mget("/resources?domainId=%s&providerResourceId=%s" % (domain_id, provider_resource_id))
            if reply.status_code == 200:
                break
            time.sleep(10)

        if reply.status_code == 200:
            resource = reply.json()["items"][0]
            return resource
        else:
            if not no_fail:
                assert False
            return None

    def get_relationship(self, source_id, target_id):
        self.logger.info("find relationship from %s to %s" % (source_id, target_id))
        reply = self.mget("/relationships?q=sourceId:%s,targetId:%s" % (source_id, target_id))
        assert reply.status_code == 200
        if reply.json()["items"]:
            relationship = reply.json()["items"][0]
        else:
            relationship = None
        return relationship

    # def get_relationships_by_target_and_capability(self, target_id, capability_name):
    #     self.log('find relationship with to %s with capability %s' % (target_id, capability_name))
    #     reply = self.mget("/relationships?q=targetId:%s,capabilityName:%s" % (target_id, capability_name))
    #     assert reply.status_code == 200
    #     relationships = reply.json()['items']
    #     return relationships

    # def get_relationships_by_source_and_capability(self, source_id, capability_name):
    #     self.log('find relationship with from %s with capability %s' % (source_id, capability_name))
    #     reply = self.mget("/relationships?q=sourceId:%s,capabilityName:%s" % (source_id, capability_name))
    #     assert reply.status_code == 200
    #     relationships = reply.json()['items']
    #     return relationships

    def add_relationship(self, name, source_id, target_id):
        self.add(
            "Relationship",
            "/relationships",
            {
                "relationshipTypeId": "tosca.relationshipTypes.MadeOf",
                "sourceId": source_id,
                "requirementName": "composed",
                "targetId": target_id,
                "capabilityName": "composable",
                "orchState": "active",
            },
        )

    def add(self, what, path, data):
        self.logger.info("Adding %s" % what)
        r = self.mpost(path, json.dumps(data))
        self.logger.info("  result: %s\n" % r.status_code)
        assert r.status_code < 210
        obj = r.json()
        self.logger.info("  %s:" % what)
        self.logger.info(obj)
        return obj

    def await_till(self, what, condFunc, interval=2.0, tmax=90.0, offset=2.0):
        t0 = time.time()
        time.sleep(offset)
        while True:
            if condFunc():
                break
            remaining = (t0 + tmax) - time.time()
            if remaining < 0:
                raise Exception("Timed out while waiting for: %s" % what)
            self.logger.info("Waiting %s for '%s' (remaining time %s)" % (interval, what, remaining))
            time.sleep(interval)
        self.logger.info("Completed: %s" % what)

    def await_resource_states(self, what, resourceId, states=["active"], interval=2.0, tmax=90.0, offset=2.0):
        t0 = time.time()
        status = ""
        time.sleep(offset)
        resource = None
        while True:
            resource = self.mget("/resources/%s" % resourceId).json()
            status = resource["orchState"]
            if status in states:
                break
            if status == "failed":
                raise Exception("%s failed with reason '%s'" % (what, resource["reason"]))
            remaining = (t0 + tmax) - time.time()
            if remaining < 0:
                raise Exception("Timed out while waiting for: %s to be in %s" % (what, states))
            self.logger.info(
                "Waiting %s seconds for '%s' to be in state %s (remaining time %s)"
                % (interval, what, states, remaining)
            )
            self.logger.info("resource at this time: %s" % (resource))
            time.sleep(interval)
        self.logger.info("Completed: %s %s" % (what, status))
        return resource

    def await_termination(self, resource_id, rname, force, tmax=300):
        try:
            self.await_till_collect_timing(
                "terminate %s" % rname,
                lambda: self.not_found_or_unknown_and_terminating(resource_id),
                interval=5,
                tmax=tmax,
            )
        except Exception:
            self.logger.info("Failed to release %s: %s" % (rname, resource_id))
            if not force:
                raise

    def not_found_or_unknown_and_terminating(self, rid):
        ret = self.mget("/resources/%s" % rid)

        if ret.status_code == 404:
            return True

        if ret.status_code != 200:
            return False

        if ret.json()["orchState"] == "unknown":
            self.logger.info("Resource is in unknown state")
            return True

        if ret.json()["orchState"] == "failed":
            assert False, "Resource is in failed state %s" % (rid)

        return False

    def await_differences_cleared(self, what, resourceId, interval=2.0, tmax=300.0):
        t0 = time.time()
        status = ""
        while True:
            resource = self.mget("/resources/%s" % resourceId).json()
            if resource["orchState"] == "failed":
                raise Exception("%s failed with reason '%s'" % (what, resource["reason"]))
            differences = resource.get("differences", [])
            if not differences:
                break
            remaining = (t0 + tmax) - time.time()
            if remaining < 0:
                raise Exception("Timed out while waiting for: %s differences to clear" % what)
            self.logger.info("Waiting %s for %s differences to clear (remaining time %s)" % (interval, what, remaining))
            time.sleep(interval)
        self.logger.info("Completed: %s %s" % (what, status))

    def delete_dependencies(
        self, resource_type, dependencies, parallel=False, force=False, force_delete_relationships=False, timeout=300
    ):
        resources = []
        matches = [d for d in dependencies if d["resourceTypeId"] == resource_type or resource_type is None]
        for d in matches:
            resources.append(
                (d["id"], "%s %s" % (d["resourceTypeId"].split(".")[2], d["label"])),
            )

        for resource_id, rname in resources:
            if force_delete_relationships:
                self.delete_relationships(resource_id)

            resp1 = self.mget("/resources/%s" % resource_id)
            resp2 = self.mget("/resources/%s/dependents" % resource_id)
            resource = resp1.json()
            dependents = resp2.json()
            self.logger.info(resource)
            self.logger.info(dependents)

            dep_count = 0
            for dep in dependents.get("items", []):
                if not dep["discovered"]:
                    dep_count += 1

            if resp1.status_code == 200 and resp2.status_code == 200:
                if dep_count <= 1 and not resource["discovered"]:
                    self.logger.info("Deleting %s ################################" % resource["resourceTypeId"])

                    self.mdelete("/resources/%s" % resource_id)

                    if not parallel:
                        self.await_termination_collect_timing(resource_id, rname, force, tmax=timeout)

        if parallel:
            for resource_id, rname in resources:
                self.await_termination_collect_timing(resource_id, rname, force, tmax=timeout)

    def delete_resource(self, resource_id):
        self.mdelete("/resources/%s" % resource_id)

    def delete_relationship(self, relationship_id):
        self.mdelete("/relationships/%s" % relationship_id)

    def delete_relationships(self, target_id):
        rels = self.mget("/relationships?q=targetId:%s" % target_id).json()
        for rel in rels["items"]:
            self.logger.info("Deleting Relationship %s" % rel["id"])
            self.mdelete("/relationships/%s" % rel["id"])

    # def delete_source_relationships(self, source_id):
    #
    #     rels = self.mget("/relationships?q=sourceId:%s" % source_id).json()
    #     for rel in rels['items']:
    #         self.log('Deleting Relationship %s' % rel['id'])
    #         self.mdelete('/relationships/%s' % rel['id'])

    # def resource_exists(self, resource_id):
    #     res = self.mget("/resources/%s" % resource_id)
    #     if res.status_code == 200:
    #         return True
    #     else:
    #         self.log("Resource ID %s not found" % resource_id)
    #         return False

    # def domain_exists(self, domain_id):
    #     res = self.mget("/domains/%s" % domain_id)
    #     if res.status_code == 200:
    #         return True
    #     else:
    #         self.log("Domain ID %s not found" % domain_id)
    #         return False

    # def domain_in_use(self, domain_id):
    #     res = self.mget("/resources?domainId=%s&q=discovered:false" % domain_id).json()
    #     if res["total"] != 0:
    #         self.log("Domain ID %s in use" % domain_id)
    #         return True
    #     else:
    #         self.log("Domain ID %s not in use" % domain_id)
    #         return False

    # def get_products_in_domain_type(self, title, domain_type, res_ids):
    #     self.log("Get %s Domain Type %s ..." % (title, domain_type))
    #     res = self.mget("/domains?q=domainType:%s" % domain_type)
    #     if res.status_code != 200:
    #         raise Exception("%s Domain Type %s not found" % (title, domain_type))
    #
    #     data = res.json()
    #     if data.get('total') != 1:
    #         raise Exception("%s Domain Type %s more than one found" % (title, domain_type))
    #
    #     return self.get_products_in_domain(title, data['items'][0]['id'], res_ids)

    # def get_products_in_domain(self, title, domain_id, res_ids):
    #     self.log("Verifying %s Domain %s exists..." % (title, domain_id))
    #     res = self.mget("/domains/%s" % domain_id)
    #     if res.status_code != 200:
    #         raise Exception("%s Domain ID %s not found" % (title, domain_id))
    #
    #     self.log("Retrieving %s Domain %s product ids..." % (title, domain_id))
    #     product_ids = self.get_product_ids_in_domain(domain_id)
    #     missing = res_ids - set(product_ids.keys())
    #     if missing:
    #         raise Exception("%s Domain ID %s missing products %s" %
    #                         (title, domain_id, ', '.join(missing)))
    #     return product_ids

    # def patch_admin_state(self, res_id, admin_state, fields=None, wait_operstatus=True, interval=2.0, tmax=300.0):
    #     self.log("Patching %s admin_state: %s" % (res_id, admin_state))
    #     data = fields if fields is not None else dict()
    #     props = data.get("properties", dict())
    #     props["adminState"] = admin_state
    #     data["properties"] = props
    #
    #     resp = self.mpatch("/resources/%s" % res_id, data)
    #     self.log("  result: %s\n" % resp.status_code)
    #     assert resp.status_code < 210
    #     if wait_operstatus:
    #         oper_status = "enabled" if admin_state == "enable" else "disabled"
    #         what = "operStatus %s to %s" % (res_id, oper_status)
    #         t0 = time.time()
    #         status = ""
    #         while True:
    #             resource = self.mget('/resources/%s' % res_id).json()
    #             differences = resource.get("differences", [])
    #             if not differences and resource["properties"].get("operStatus") == oper_status:
    #                 break
    #             if resource['orchState'] == 'failed':
    #                 raise Exception("%s failed with reason '%s'" % (what, resource['reason']))
    #             remaining = (t0 + tmax) - time.time()
    #             if remaining < 0:
    #                 raise Exception("Timed out while waiting for: %s differences to clear" % what)
    #             self.log("Waiting %s for %s differences to clear (remaining time %s)" % (interval, what, remaining))
    #             time.sleep(interval)
    #         self.log("Completed: %s %s" % (what, status))

    # def oper_status_equals(self, res_id, oper_status):
    #     resp = self.mget('/resources/%s' % res_id)
    #     assert resp.status_code < 210
    #     obj = resp.json()
    #     if obj["properties"]["operStatus"] == oper_status:
    #         return True
    #     else:
    #         return False

    def create_active_resource(
        self, title, parent_res_id, body, wait_active=True, waittime=300, interval=5, create_relationship=True
    ):
        self.logger.info("Creating %s ################################" % title)
        resp = self.add("Resource", "/resources", body)
        resp_id = resp["id"]

        if create_relationship is True and parent_res_id is not None:
            self.add_relationship(title, parent_res_id, resp_id)

        if wait_active:
            resource = self.await_resource_states_collect_timing(title, resp_id, interval=interval, tmax=waittime)
        else:
            resource = self.mget("/resources/%s" % resp_id).json()

        provider_res_id = resource.get("providerResourceId")
        # FIXME: VM is not returning a providerResourceId so allowing None
        self.logger.info("%s Provider ID: %s" % (title, provider_res_id))
        return self.ResourceInfo(resource, resp_id, provider_res_id)

    def get_provider_product_ids_string(self, resource_ids, resources=None):
        try:
            rid2resource = {}
            product_ids = set()
            ids_string = ""
            if not resources:
                for resource_id in set(resource_ids):
                    resource = self.bpo.resources.get(resource_id, obfuscate=True)
                    rid2resource[resource_id] = resource
            else:
                rid2resource = {resource["id"]: resource for resource in resources}
            for resource in rid2resource.values():
                product = self.bpo.products.get(resource["productId"])
                # try to enhance info by looking at the product
                # so that instead of tosca.resourceTypes.FRE,
                # we can show urn:cyaninc:bp:product:junipereq:FRE
                if "providerProductId" in product:
                    product_ids.add(product["providerProductId"])
                else:
                    product_ids.add(resource["resourceTypeId"])
            ids_string = str(product_ids)
        except Exception:
            ids_string = "{} resource(s)".format(len(set(resource_ids)))
        return ids_string

    def await_active_collect_timing(self, resource_ids, interval=1.0, tmax=90.0):
        template = "METRICS|what: await_active|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.bpo.resources.await_active(resource_ids, interval=interval, max=tmax)
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            resources_str = self.get_provider_product_ids_string(resource_ids, resources=return_value)
            msg = template.format(flag, float(str(tmax)), float(str(elapsed)), resources_str)
            self.logger.info(msg)

    def await_differences_cleared_collect_timing(self, resource_label, resource_id, interval=1.0, tmax=300.0):
        template = "METRICS|what: await_differences_cleared|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.await_differences_cleared(resource_label, resource_id, interval=interval, tmax=tmax)
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            resources_str = self.get_provider_product_ids_string([resource_id], resources=return_value)
            msg = template.format(flag, float(str(tmax)), float(str(elapsed)), resources_str)
            self.logger.info(msg)

    def await_operation_successful_collect_timing(self, resource_id, operation_id, tmax=300.0, interval=5.0):
        template = "METRICS|what: await_operation_successful|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.bpo.resources.await_operation_successful(
                resource_id, operation_id, max=tmax, interval=interval
            )
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            resources_str = self.get_provider_product_ids_string([resource_id], resources=return_value)
            msg = template.format(flag, float(str(tmax)), float(str(elapsed)), resources_str)
            self.logger.info(msg)

    def await_termination_collect_timing(self, resource_id, rname, force, tmax=300):
        template = "METRICS|what: await_termination|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.await_termination(resource_id, rname, force, tmax=tmax)
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            resources_str = self.get_provider_product_ids_string([resource_id], resources=return_value)
            msg = template.format(flag, float(str(tmax)), float(str(elapsed)), resources_str)
            self.logger.info(msg)

    def await_resource_states_collect_timing(
        self, what, resource_id, states=frozenset(["active"]), interval=2.0, tmax=90.0, offset=2.0
    ):
        template = "METRICS|what: {}|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.await_resource_states(
                what, resource_id, states=states, interval=interval, tmax=tmax, offset=offset
            )
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            resources_str = self.get_provider_product_ids_string([resource_id], resources=[return_value])
            msg = template.format(what, flag, float(str(tmax)), float(str(elapsed)), resources_str)
            self.logger.info(msg)

    def await_till_collect_timing(self, what, condfunc, interval=2.0, tmax=90.0, offset=2.0):
        template = "METRICS|what: await_till|status: {}|max: {:.2f}|elapsed: {:.2f}|resources: {}"
        return_value = None
        try:
            flag = "SUCCESS"
            start = time.time()
            return_value = self.await_till(what, condfunc, interval=interval, tmax=tmax, offset=offset)
            return return_value
        except Exception as e:
            flag = "TIMEOUT" if "Timed out" in str(e) else "FAILED"
            raise e
        finally:
            elapsed = time.time() - start
            msg = template.format(flag, float(str(tmax)), float(str(elapsed)), condfunc)
            self.logger.info(msg)

    # def calc_dotted_netmask(self, mask):
    #     bits = 0xffffffff ^ (1 << 32 - mask) - 1
    #     return inet_ntoa(pack('>I', bits))

    # def dottedQuadToNum(self, ip):
    #     # convert decimal dotted quad string to long integer
    #     return unpack('>L', inet_aton(ip))[0]
    #
    # def numToDottedQuad(self, n):
    #     # convert long int to dotted quad string
    #     return inet_ntoa(pack('>L', n))

    # def makeMask(self, n):
    #     return a mask of n bits as a long integer
    #    return (2L << n - 1) - 1 if n != 0 else 0
    #
    # def ipToNetAndHost(self, ip, maskbits):
    #     return tuple (network, host) dotted-quad addresses given IP and
    #     mask size
    #    n = self.dottedQuadToNum(ip)
    #    m = self.makeMask(32 - maskbits)
    #    host = n & m
    #     net = n - host
    #     return self.numToDottedQuad(net), self.numToDottedQuad(host)

    # def pingit(self, access_ip, port, remain, interval):
    #     s = socket(AF_INET, SOCK_STREAM)
    #     s.settimeout(10)
    #     try:
    #         self.log("Checking VNF connectivity (%d retries remained)" % remain)
    #         s.connect((access_ip, port))
    #     except Exception:
    #         if remain > 0:
    #             self.log("Cannot connect to VNF. Retry in %s seconds" % interval)
    #         else:
    #             self.log("Cannot connect to VNF")
    #         s.close()
    #         return 1
    #     while True:                    # If connected to host
    #         self.log("VNF Connected!")
    #         s.close()
    #         return 0
    #
    # def check_ip_connectivity(self, ip_address):
    #     self.log("Verifying connection to VNF at %s" % ip_address)
    #     device_connected = False
    #     max_conn_retries = 30
    #     conn_retry_interval = 10
    #     for i in range(max_conn_retries):
    #         ret = self.pingit(ip_address, 22,
    #                           (max_conn_retries - i - 1), conn_retry_interval)
    #         if ret == 0:
    #             device_connected = True
    #             break
    #         time.sleep(conn_retry_interval)
    #
    #     if not device_connected:
    #         raise Exception("Unable to connect to VNF device at %s" % (ip_address))

    # def subnetToGwMask(self, subnet):
    #
    #     address = subnet.split('/')[0]
    #
    #     gateway = subnet.split('/')[0].split('.')
    #     gateway[3] = "1"
    #     gateway = ".".join(gateway)
    #
    #     mask = int(subnet.split('/')[1])
    #     mask = [str((255 << 8) >> min(8, (max(mask, 0) - 0)) & 255),
    #             str((255 << 8) >> min(8, (max(mask, 8) - 8)) & 255),
    #             str((255 << 8) >> min(8, (max(mask, 16) - 16)) & 255),
    #             str((255 << 8) >> min(8, (max(mask, 24) - 24)) & 255),
    #             ]
    #     mask = ".".join(mask)
    #
    #     return address, gateway, mask
