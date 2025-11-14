#!/usr/bin/python

from requests.packages.urllib3.exceptions import InsecureRequestWarning
import argparse
import requests
import json
import copy
import traceback
import logging
import logging.config

logging_init_fname = "log_config.ini"
logger = None
DEFAULT_RES_PAGE = 50


def dumpErr(msg):
    # print msg
    logger.error(msg)


def dumpDebug(msg):
    # print msg
    logger.debug(msg)


def dumpInfo(msg):
    # print msg
    logger.info(msg)


# Ignore warnings about unverified https requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class BPO(object):
    auth_url = 'bpocore/authentication/api/v1/tokens'

    def __init__(self, host, port, user, password, tenant):
        self.host = host
        self.user = user
        self.tenant = tenant
        self.port = port
        self.password = password
        self.headers = {"content-type": "application/json"}
        self.token = None
        scheme = 'http' if port != 443 else 'https'
        self.url = '{}://{}:{}/'.format(scheme, host, port)
        self.authenticate()

    def authenticate(self):
        ''' Authenticate w/ bpocore '''

        if self.port != 443:
            return

        auth_post_data = {
            "name": self.user,
            "password": self.password,
            "tenant": {
                "name": self.tenant
            }
        }

        url = "{}{}".format(self.url, self.auth_url)
        logger.debug(
            'authenticate \n url:{}\n headers:{}\n payload:{}'.format(url,
                                                                      {"content-type": "application/json"},
                                                                      json.dumps(auth_post_data)))

        response = requests.post(url,
                                 verify=False,
                                 headers={"content-type": "application/json"},
                                 data=json.dumps(auth_post_data))

        if response.status_code != 201:
            raise RuntimeError("Unable to authtenticate with host: {}".format(self.host))
        else:
            self.token = response.headers.get('X-Subject-Token')
            self.headers.update(
                {"Authorization": "token {}".format(response.headers.get('X-Subject-Token'))})

    def do_post(self, query, data):
        logger.debug('POST \n url:{}\n headers:{}\n payload:{}'.format(self.url + query,
                                                                       self.headers,
                                                                       json.dumps(data)))
        r = requests.post(self.url + query, verify=False, headers=self.headers, data=json.dumps(data))
        logger.debug('RESP {}'.format(r))
        return r.json()

    def do_put(self, query, data):
        logger.debug('PUT \n url:{}\n headers:{}\n'.format(self.url + query,
                                                           self.headers))
        r = requests.put(self.url + query, verify=False, headers=self.headers)
        logger.debug('RESP {}'.format(r))
        return r.json()

    def do_delete(self, query):
        logger.debug('DELETE \n url:{}\n headers:{}\n'.format(self.url + query,
                                                              self.headers))
        r = requests.delete(self.url + query, verify=False, headers=self.headers)
        logger.debug('RESP {}'.format(r))
        return r

    def do_get(self, query):
        logger.debug('GET \n url:{}\n headers:{}\n'.format(self.url + query,
                                                           self.headers))
        r = requests.get(self.url + query, verify=False, headers=self.headers)
        logger.debug('RESP {}'.format(r))
        return r.json()

    def mget(self, query):
        r = requests.get(self.url + query, verify=False, headers=self.headers)
        return r

    def get_resources(self, resource_type=None):
        query = "bpocore/market/api/v1/resources"
        if resource_type:
            query += "?resourceTypeId=%s" % resource_type
        return self.do_get(query).get('items', [])

    def get_resources_offset(self, resource_type=None, offset=0, limit=1000):
        query = "bpocore/market/api/v1/resources"
        if resource_type:
            query += "?resourceTypeId=%s&offset=%d&limit=%d" % (resource_type, offset, limit)
        return self.do_get(query).get('items', [])

    def get_resources_total(self, resource_type=None):
        query = "bpocore/market/api/v1/resources"
        if resource_type:
            query += "?resourceTypeId=%s&offset=0&limit=0" % resource_type
        return self.do_get(query)

    def get_resource_dependencies_total(self, resource_id, query="", recursive="false", pageToken=None):
        if pageToken:
            msg = "bpocore/market/api/v1/resources/%s/dependencies?recursive=%s%s&offset=%d&limit=%d&pageToken=%s" \
                  % (resource_id, recursive, query, 0, 0, pageToken)
        else:
            msg = "bpocore/market/api/v1/resources/%s/dependencies?recursive=%s%s&offset=%d&limit=%d" \
                  % (resource_id, recursive, query, 0, 0)
        return self.do_get(msg)

    def get_resource(self, resource_id):
        return self.do_get("bpocore/market/api/v1/resources/%s" % resource_id)

    def get_products(self):
        return self.do_get("bpocore/market/api/v1/products")["items"]

    def get_products_by_domid(self, id):
        return self.do_get("bpocore/market/api/v1/domains/{}/products?includeInactive=false&offset=0&limit=1000".format(id))["items"]

    def get_resource_types(self):
        return self.do_get("bpocore/market/api/v1/resource-types")["items"]

    def get_resource_type(self, resource_type):
        return self.do_get("bpocore/market/api/v1/resource-types/%s/products" % resource_type)["items"]

    def get_domains(self):
        return self.do_get("bpocore/market/api/v1/domains")["items"]

    def delete_product(self, product_id):
        # print "-> Deleting product %s" % product_id
        self.do_delete("bpocore/market/api/v1/products/%s" % product_id)

    def get_tenants(self):
        return self.do_get("tron/api/v1/tenants/")["results"]

    def get_tenant_uuid(self, name):
        tenants = self.get_tenants()
        return [t for t in tenants if t["name"] == name][0]["uuid"]


class Session():
    def __init__(self, host, port, user, password, tenant):
        self.bpohost = host
        self.bpo = BPO(host, port, user, password, tenant)

        # NFs dups
        self.nfsTotalNfs = 0
        self.nfsTotalDuplicates = 0
        self.nfsDupList = []
        self.nfsStatDict = {
            "items": [],
            "summary": {}
        }
        self.nfsDupStatDict = {
            "res": {
                "nf": {
                    "details": {
                        "total": 0,
                        "duplicates": 0
                    },
                    "name": ""
                }
            }
        }

        # Resources
        self.resTotalResource = 0
        self.resTotalFailed = 0
        self.resFailedList = []
        self.resStatDict = {
            "items": [],
            "summary": {}
        }
        self.resFailedStatDict = {
            "res": {
                "failures": {
                    "name": "",
                    "details": {
                        "total": 0,
                        "failed": 0,
                        "success": 0
                    }
                }
            }
        }

    def utilGetProduct(self, resourceTypeId):
        products = self.bpo.get_products()
        product = None
        if products:
            product = [p for p in products if p["resourceTypeId"] == resourceTypeId][0]
        return product

    def utilGetResourcePages(self, resourceTypeId, infofunc):
        rnfs = []
        total = 0
        tr = self.bpo.get_resources_total(resourceTypeId)
        if tr is None:
            raise
        if tr['total'] < DEFAULT_RES_PAGE:
            trs = tr['total']
            rs = self.bpo.get_resources_offset(resourceTypeId, 0, trs)
            if rs is None:
                raise
            for r in rs:
                rnfi = infofunc(r)
                rnfs.append(rnfi)
                total += 1
        else:
            trs = int(tr['total'])
            num = (trs / DEFAULT_RES_PAGE) + 1
            # for tr in range(3):
            for tr in range(num):
                rs = self.bpo.get_resources_offset(resourceTypeId, int(tr) * DEFAULT_RES_PAGE, DEFAULT_RES_PAGE)
                if rs is None:
                    raise
                for r in rs:
                    rnfi = infofunc(r)
                    rnfs.append(rnfi)
                    total += 1
        return total, rnfs

    def utilGetResourceDepsPages(self, resourceId, filter, recursive):
        total = 0
        nrs = self.bpo.get_resource_dependencies_total(resourceId, filter, recursive, None)
        while nrs:
            if nrs and 'total' in nrs:
                total += nrs['total']
            crs = self.bpo.get_resource_dependencies_total(resourceId, filter, recursive, nrs['nextPageToken'])
            if crs['nextPageToken'] == nrs['nextPageToken']:
                break
            nrs = crs

        return total

    def nfStats(self, resourceTypeId, total, duplist):
        rd = self.nfsDupStatDict
        rd['res']['nf']['name'] = resourceTypeId
        rd['res']['nf']['details']['total'] = total
        rd['res']['nf']['details']['duplicates'] = len(duplist[resourceTypeId])
        return rd

    def nfInfodict(self, res):
        # typeGroup = ""
        ipAddress = ""
        serialNumber = ""
        nf = {"orchState": "",
              "resourceId": "",
              "ipAddress": ipAddress,
              "serialNumber": serialNumber,
              "check": False}
        if 'properties' in res:
            if 'ipAddress' in res['properties']:
                ipAddress = res['properties']['ipAddress']
            if 'serialNumber' in res['properties']:
                serialNumber = res['properties']['serialNumber']
            nf = {"orchState": res['orchState'],
                  "resourceId": res['id'],
                  "ipAddress": ipAddress,
                  "serialNumber": serialNumber,
                  "check": False}
        return nf

    def nfListDupNetworkFunction(self, resourceTypeId):
        nfsStats = []
        rs = []
        rt, rs = self.utilGetResourcePages(resourceTypeId, self.nfInfodict)
        if rt > 0 and rs:
            # find dups on first pass searching through 1 table,
            # should be quite efficient...
            rtid = json.dumps(resourceTypeId).strip("\"")
            dupes = {}
            dupes[rtid] = []
            for n, ernf in enumerate(rs):
                append = False
                tdupes = []
                if len(ernf['ipAddress'].split('.')) > 0:
                    ternf = ernf['ipAddress'].split('.')[0]
                for crnf in rs[n + 1:]:
                    if len(crnf['ipAddress'].split('.')) > 0:
                        tcrnf = crnf['ipAddress'].split('.')[0]
                    if ternf == tcrnf and ernf['serialNumber'] == crnf['serialNumber']:
                        if crnf['check'] is False:
                            tdupes.append(crnf)
                            crnf['check'] = True
                            append = True
                        if ernf['check'] is False:
                            tdupes.append(ernf)
                            ernf['check'] = True
                            append = True
                if append:
                    dupes[rtid].append(tdupes)
                    for tdup in tdupes:
                        tdup.pop('check', None)
            self.nfsDupList.append(dupes)
            # stats
            self.nfsTotalNfs += rt
            self.nfsTotalDuplicates += len(dupes[resourceTypeId])
            nfsStats.append(copy.deepcopy(self.nfStats(resourceTypeId, rt, dupes)))

            return nfsStats

    def nfListDupNetworkFunctions(self, resourceTypeId):
        nfsStats = []
        if resourceTypeId == "None":
            ps = self.bpo.get_products()
            if ps is None:
                raise
            for p in ps:
                if p['resourceTypeId'].find('.resourceTypes.NetworkFunction') != -1:
                    rl = self.nfListDupNetworkFunction(p['resourceTypeId'])
                    if rl:
                        nfsStats.append(rl)
        else:
            rl = s.nfListDupNetworkFunction(resourceTypeId)
            if rl:
                nfsStats.append(rl)
        if not self.nfsDupList:
            raise
        if not nfsStats:
            raise
        dumpInfo("-------------NF duplicate list-------------")
        dumpInfo(json.dumps(self.nfsDupList))
        dumpInfo("-------------NF duplicate stats-------------")
        self.nfsStatDict['items'] = nfsStats
        self.nfsStatDict['summary']['total'] = self.nfsTotalNfs
        self.nfsStatDict['summary']['duplicates'] = self.nfsTotalDuplicates
        dumpInfo(json.dumps(self.nfsStatDict))

    def resStats(self, resourceTypeId, total, failList):
        rd = self.resFailedStatDict
        rd['res']['failures']['name'] = resourceTypeId
        rd['res']['failures']['details']['total'] = total
        rd['res']['failures']['details']['failed'] = len(failList)
        rd['res']['failures']['details']['success'] = total - len(failList)
        return rd

    def resInfoDict(self, res):
        nf = {"label": res['label'],
              "id": res['id'],
              "orchState": res['orchState']}
        return nf

    def resListFailure(self, resourceTypeId):
        resStats = []
        trf = {}
        rtid = json.dumps(resourceTypeId).strip("\"")
        trf[rtid] = []
        rt, rs = self.utilGetResourcePages(resourceTypeId, self.resInfoDict)
        for r in rs:
            if r['orchState'] == 'failed':
                r.pop('orchState', None)
                trf[rtid].append(r)
        self.resFailedList.append(trf)
        # stats
        self.resTotalResource += rt
        self.resTotalFailed += len(trf[rtid])
        resStats.append(copy.deepcopy(self.resStats(resourceTypeId, rt, trf[rtid])))

        return resStats

    def resListFailures(self, resourceTypeId):
        # print "This operation might take a while to finish..."
        resStats = []
        if resourceTypeId == "None":
            ps = self.bpo.get_products()
            if ps is None:
                raise
            for n, p in enumerate(ps):
                # if n <= 3:
                rl = self.resListFailure(p['resourceTypeId'])
                if rl:
                    resStats.append(rl)
        else:
            rl = self.resListFailure(resourceTypeId)
            if rl:
                resStats.append(rl)
        if not self.resFailedList:
            raise
        if not resStats:
            raise
        dumpInfo("-------------Resource list-------------")
        dumpInfo(json.dumps(self.resFailedList))
        dumpInfo("-------------Resource stats-------------------")
        self.nfsStatDict['items'] = resStats
        self.nfsStatDict['summary']['total'] = self.resTotalResource
        self.nfsStatDict['summary']['failed'] = self.resTotalFailed
        self.nfsStatDict['summary']['success'] = self.resTotalResource - self.resTotalFailed
        dumpInfo(json.dumps(self.nfsStatDict))

    def resRawStatistic(self, resourceTypeId):
        trs = []
        rt, rs = self.utilGetResourcePages(resourceTypeId, self.resInfoDict)
        for r in rs:
            if r['orchState'] == 'active':
                r.pop('orchState', None)
                trs.append(r)
        tdeps = 0
        for tr in trs:
            ndeps = self.utilGetResourceDepsPages(tr['id'], "&q=discovered:false", "true") + 1
            dumpInfo("Dependency count (not discovered) of %s %s = %s" % (resourceTypeId, tr['label'], ndeps))
            tdeps += ndeps
        dumpInfo("%s count: %s" % (resourceTypeId, len(trs)))
        dumpInfo("Dependency count total (not discovered) of all %s: %s" % (resourceTypeId, tdeps))
        avg = str(float(tdeps) / float(len(trs)))
        dumpInfo("Average: %s sub-resources per %s" % (avg, resourceTypeId))

    def resStatistics(self, resourceTypeId):
        self.resRawStatistic(resourceTypeId)


if __name__ == "__main__":

    def argsChecker(args):
        # add argument checker here...
        sts = "success"
        if args.action == 'resource-stats-deps' and args.restypeid == 'None':
            sts = "failure"
            dumpErr("error --restypeid is {}, must specify resource type id for --action {}".format(
                args.restypeid, args.action))
        return sts

    # create log
    logging.config.fileConfig(logging_init_fname)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description='charter BP tools ver.0.0.1')
    parser = argparse.ArgumentParser(description='log init: log_config.ini, log location: ./log')
    parser.add_argument("--host", help="BPO IP Address", required=True)
    parser.add_argument("--username", help="BPO Username (default admin)", default="admin")
    parser.add_argument("--password", help="BPO Password (default adminpw)", default="adminpw")
    parser.add_argument("--tenant", help="BPO Tenant   (default master)", default="master")
    parser.add_argument("--restypeid", help="BPO product resource type id  (default none)", default="None")
    parser.add_argument("--ppr", help="BPO pages per-request (default 50 entries)", default=50)
    parser.add_argument("--action", help="Actions", choices=['list-dup-network-functions',
                                                             'list-failed-network-services',
                                                             'list-failed-resources',
                                                             'list-all',
                                                             'resource-stats-deps'])
    args = parser.parse_args()
    try:
        logger.debug("---process start---")

        s = Session(args.host, 443, args.username, args.password, args.tenant)

        if argsChecker(args) == "success":
            if args.ppr:
                DEFAULT_RES_PAGE = args.ppr
                logger.info("BPO pages per-request {}".format(DEFAULT_RES_PAGE))
            if args.action == 'list-dup-network-functions':
                s.nfListDupNetworkFunctions(args.restypeid)
            if args.action == 'list-failed-network-services':
                s.resListFailures("charter.resourceTypes.NetworkService")
            if args.action == 'list-failed-resources':
                s.resListFailures(args.restypeid)
            if args.action == 'list-all':
                s.nfListDupNetworkFunctions(args.restypeid)
                s.resListFailures(None)
            if args.action == 'resource-stats-deps':
                s.resStatistics(args.restypeid)

        logger.debug("---process end---")
        logger.debug("")

    except Exception:
        tb = traceback.format_exc()
        dumpErr(tb)
    else:
        tb = ""
