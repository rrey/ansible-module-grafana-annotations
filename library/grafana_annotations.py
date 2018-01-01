#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64encode
import urllib
import time
import json
try:
    import httplib
except ImportError:
    # Python 3
    import http.client as httplib

API_URI = "/api/annotations"

DOCUMENTATION = '''
---
module: grafana_annotations
short_description: Interact with Grafana REST API to create annotations.
options:
    addr:
        required: true
        description:
            - address of the grafana REST API
    user:
        required: false
        description:
            - user for the http authentication on the REST API
    passwd:
        required: false
        description:
            - password for the http authentication on the REST API
    time:
        required: false
        description:
            - epoch datetime in milliseconds.
              If not specified, the current localtime is used.
    timeEnd:
        required: false
        description:
            - epoch datetime in milliseconds, automatically define the
            annotation as a region annotation.
    tags:
        required: false
        description:
            - Associate tags to the annotation
        default: ["ansible"]
    text:
        required: true
        description:
            - Text to be displayed in the annotation
    secure:
        required: false
        default: false
        description:
            - If true, an https connection will be established with the
            Grafana server.
'''

EXAMPLES = '''
- name: Create a global annotation
  grafana_annotations:
    addr: "10.4.3.173:8080"
    user: "grafana_login"
    passwd: "grafana_password"
    text: "Started update of production environment"

- name: Create a global annotation
  grafana_annotations:
    addr: "10.4.3.173:8080"
    user: "grafana_login"
    passwd: "grafana_password"
    time: 1513000095
    text: "Planned intervention on production server"

- name: Create a global region annotation
  grafana_annotations:
    addr: "10.4.3.173:8080"
    user: "grafana_login"
    passwd: "grafana_password"
    time: 1513000095
    timeEnd: 1513005095
    text: "Execution of the xxxx playbook"

'''


def build_search_uri(uri, annotation):
    """Return the search uri based on the annotation"""
    params = []
    tags = annotation.get("tags", None)
    if tags:
        for tag in tags:
            params.append("tags=%s" % urllib.quote_plus(tag))
    if annotation.get('time', None):
        params.append("from=%s" % annotation.get('time'))
    if annotation.get('timeEnd', None):
        params.append("to=%s" % annotation.get('timeEnd'))
    else:
        params.append("to=%s" % (int(time.time()) * 1000))

    if params:
        uri = "%s?%s" % (uri, '&'.join(params))
    return uri


def default_filter(annos, annotation):
    """default filter comparing 'time', 'text' and 'tags' parameters"""
    result = []
    for anno in annos:
        for key in ['time', 'text', 'tags']:
            if anno.get(key) != annotation.get(key):
                continue
        result.append(anno)
    return result


def region_filter(annos, annotation):
    """filter for Region annotations.
    The 'time' parameter can match either 'time' or 'timeEnd' parameters.
    """
    result = []
    for anno in annos:
        time = annotation.get("time")
        timeEnd = annotation.get("timeEnd")
        for key in ['text', 'tags']:
            if anno.get(key) != annotation.get(key):
                continue
        if anno.get("regionId") == 0:
            continue
        if anno.get("time") not in [time, timeEnd]:
            continue
        result.append(anno)
    return result


def filter_annotations(annos, annotation):
    """Filter the annotations that does not match `annotation`"""
    if annotation.get("isRegion", False) is True:
        return region_filter(annos, annotation)
    return default_filter(annos, annotation)


class GrafanaManager(object):
    """Manage communication with grafana HTTP API"""
    def __init__(self, addr, user=None, passwd=None, secure=False):
        self.addr = addr
        self.headers = {"Content-Type": "application-json",
                        "Accept": "application/json"}
        self.secure = secure
        if user and passwd:
            cred = "%s:%s" % (user, passwd)
            authorisation = "Basic %s" % b64encode(cred).decode('ascii')
            self.headers["Authorization"] = authorisation

    def query(self, method, uri, data=None):
        http = httplib.HTTPConnection(self.addr)
        if self.secure:
            http = httplib.HTTPSConnection(self.addr)
        http.request(method, uri, data, headers=self.headers)
        response = http.getresponse()
        return response.status, json.loads(response.read())

    def get_annotation(self, annotation):
        """Search for the annotation in grafana"""
        uri = build_search_uri(API_URI, annotation)
        status, annos = self.query("GET", uri)
        if status != 200:
            raise Exception("Grafana answered with HTTP %d" % status)
        return filter_annotations(annos, annotation)

    def create_annotation(self, annotation):
        """Submit an annotation to grafana"""
        status, data = self.query("POST", API_URI, json.dumps(annotation))
        if status != 200:
            raise Exception("Grafana answered with HTTP %d" % response.status)
        return data


def main():
    module = AnsibleModule(
        argument_spec={
            'addr': dict(required=True),
            'user': dict(required=False, default=None),
            'passwd': dict(required=False, default=None),
            'time': dict(required=False, default=None),
            'timeEnd': dict(required=False, default=None, type=int),
            'tags': dict(required=False, default=[], type=list),
            'text': dict(required=True, type=str),
        },
        supports_check_mode=False
    )

    addr = module.params['addr']
    user = module.params['user']
    passwd = module.params['passwd']
    _time = module.params['time']
    time_end = module.params['timeEnd']
    tags = ["ansible"] + module.params['tags']
    text = module.params['text']

    grafana = GrafanaManager(addr, user=user, passwd=passwd)

    if not _time:
        _time = int(time.time()) * 1000
    else:
        _time = int(_time) * 1000

    annotation = {"time": _time, "tags": tags, "text": text}

    if time_end:
        annotation['timeEnd'] = time_end * 1000
        annotation['isRegion'] = True

    changed = False
    try:
        annotations = grafana.get_annotation(annotation)
        if not annotations:
            annotation = grafana.create_annotation(annotation)
            annotations = [annotation]
            changed = True
    except Exception as err:
        module.fail_json(msg=str(err), annotation=annotation)
    module.exit_json(annotations=annotations, changed=changed)


#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
