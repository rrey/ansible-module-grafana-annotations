#!/usr/bin/env python
# -*- coding: utf-8 -*-

#pylint: disable=missing-docstring

import httplib
import json
from base64 import b64encode

DOCUMENTATION = '''
---
module: grafana_annotations
short_description: Interact with spark rest api
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
        required: true
        description:
            - epoch datetime in milliseconds.
    timeEend:
        required: false
        description:
            - epoch datetime in milliseconds, automatically define the
            annotation as a region annotation.
    tags:
        required: false
        description:
            - Associate tags to the annotation
        default: []
    text:
        required: true
        description:
            - Text to be displayed in the annotation
'''

EXAMPLES = '''
- name: Create a global annotation
  grafana_annotation:
    addr: "10.4.3.173:8080"
    user: "grafana_login"
    passwd: "grafana_password"
    time: 1513000095
    text: "Started update of production environment"

- name: Create a global region annotation
  grafana_annotation:
    addr: "10.4.3.173:8080"
    user: "grafana_login"
    passwd: "grafana_password"
    time: 1513000095
    timeEnd: 1513005095
    text: "Execution of the xxxx playbook"

'''

class GrafanaManager(object):
    """Manage communication with grafana HTTP API"""
    def __init__(self, addr, user=None, password=None):
        self.conn = httplib.HTTPConnection(addr)
        self.set_headers(user, password)

    def set_headers(self, user, passwd):
        self.headers = {"Content-Type": "application-json"}
        if user and passwd:
            self.headers["Authorization"] = b64encode("%s:%s" % (user, passwd)).decode('ascii')

    def get_annotation(self, annotation):
        uri = "/api/annotations"

        params = ""
        for key, val in annotation.iteritems():
            if key == "tags":
                for tag in val:
                    params += "&tags=%s" % tag
            else:
                params += "&%s=%s" % (key, val)

        if params:
            uri = "%s?%s" % (uri, params)

        self.conn.request("POST", uri, headers=self.headers)
        response = self.conn.getresponse()
        body = response.read()
        return json.loads(body)

    def create_annotation(self, annotation):
        uri = "/api/annotations"

        self.conn.request("POST", uri, annotation, headers=self.headers)
        response = self.conn.getresponse()
        body = response.read()
        return json.loads(body)


def main():
    module = AnsibleModule(     #pylint: disable=undefined-variable
        argument_spec={
            'addr': dict(required=True),
            'user': dict(required=False, default=None),
            'passwd': dict(required=False, default=None),
            'time': dict(required=True),
            'timeEnd': dict(required=False, default=None),
            'tags': dict(required=False, default=None, type=list),
            'text': dict(required=True, type=str),
        },
        supports_check_mode=False
    )

    addr = module.params['addr']
    user = module.params['user']
    passwd = module.params['passwd']
    time = module.params['time']
    time_end = module.params['timeEnd']
    tags = module.params['tags']
    text = module.params['text']

    grafana = GrafanaManager(addr, user=user, password=passwd)

    annotation = {
        "time": time,
        "tags": tags,
        "text": text,
    }

    if time_end:
        annotation['timeEnd'] = time_end
        annotation['isRegion'] = True

    changed = False
    try:
        res = grafana.get_annotation(annotation)
        if len(res) > 1:
            module.fail_json(msg="Found more than one matching annotation",
                             annotations=res)
        if not res:
            res = grafana.create_annotation(annotation)
            changed = True
    except Exception as err:
        module.fail_json(msg=str(err), annotation=annotation)

    module.exit_json(
        annotation=res,
        changed=changed
    )

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
main()
