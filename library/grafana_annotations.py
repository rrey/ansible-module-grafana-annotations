#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import time
import json

from ansible.module_utils.urls import fetch_url, basic_auth_header, url_argument_spec
from ansible.module_utils.basic import *

DOCUMENTATION = '''
---
module: grafana_annotations
description: Allows to create annotations in Grafana from playbooks.
short_description: Create annotations in Grafana through the dedicated API.
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
    token:
        required: false
        description:
            - Grafana API token
    time:
        required: false
        description:
            - epoch datetime in seconds.
              If not specified, the current localtime is used.
    tags:
        required: false
        description:
            - Associate tags to the annotation
        default: ["ansible"]
    text:
        required: true
        description:
            - Text to be displayed in the annotation
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
'''


def default_filter(annos, annotation):
    """default filter comparing 'time', 'text' and 'tags' parameters"""
    result = []
    for anno in annos:
        if anno.get('time') != annotation.get('time'):
            continue
        if anno.get('text') != annotation.get('text'):
            continue
        if anno.get('tags') != annotation.get('tags'):
            continue
        result.append(anno)
    return result


def filter_annotations(annos, annotation):
    """Filter the annotations that does not match `annotation`"""
    annotation = annotation.as_dict()
    return default_filter(annos, annotation)


class GrafanaManager(object):
    """Manage communication with grafana HTTP API"""

    def __init__(self, module, url, url_username, url_password, token):
        self.module = module
        self.url = url
        self.headers = {"Content-Type": "application-json", "Accept": "application/json"}
        if url_username and url_password:
            authorization = basic_auth_header(url_username, url_password)
        elif token:
            authorization = "Bearer %s" % token
        self.headers["Authorization"] = authorization


    def build_search_uri(self, annotation):
        """Return the search url based on the annotation"""
        params = []
        annotation = annotation.as_dict()
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
            uri = "%s?%s" % (self.url, '&'.join(params))
        return uri


    def get_annotation(self, annotation):
        """Search for the annotation in grafana"""
        url = self.build_search_uri(annotation)
        resp, info = fetch_url(self.module, url, data=annotation.as_json(), headers=self.headers, method="GET")

        status_code = info["status"]
        if status_code != 200:
            raise Exception("Grafana answered with HTTP %d" % status_code)

        annos = json.loads(resp.read())
        return filter_annotations(annos, annotation)


    def send_annotation(self, annotation):
        resp, info = fetch_url(self.module, self.url, data=annotation.as_json(), headers=self.headers, method="POST")

        status_code = info["status"]
        if not 200 <= status_code <= 299:
            raise Exception("Grafana answered with HTTP %d" % status_code)
        return resp.read()


# {{{ Annotation object

class Annotation(object):

    def __init__(self, text, tags, tstamp=None):
        self.text = text
        self.tags = tags
        self._set_time(tstamp)

    def _set_time(self, tstamp=None):
        if tstamp:
            self.time = int(tstamp) * 1000
        else:
            self.time = int(time.time()) * 1000

    def as_dict(self):
        return self.__dict__

    def as_json(self):
        return json.dumps(self.__dict__)

# }}}


def main():
    base_arg_spec = url_argument_spec()
    base_arg_spec.update(
        token=dict(required=False, default=None, no_log=True),
        time=dict(required=False, default=None),
        tags=dict(required=False, default=[], type='list'),
        text=dict(required=True, type='str'),
    )
    module = AnsibleModule(
        argument_spec=base_arg_spec,
        supports_check_mode=False,
        mutually_exclusive=[['url_username', 'token']]
    )

    url = module.params['url']
    url_username = module.params['url_username']
    url_password = module.params['url_password']
    token = module.params['token']
    tstamp = module.params['time']
    tags = ["ansible"] + module.params['tags']
    text = module.params['text']

    annotation = Annotation(text, tags, tstamp=tstamp)

    grafana = GrafanaManager(module, url, url_username, url_password, token)


    changed = False
    try:
        annotations = grafana.get_annotation(annotation)
        if not annotations:
            annotation = grafana.send_annotation(annotation)
            annotations = [annotation]
            changed = True
    except Exception as err:
        module.fail_json(msg=str(err), annotation=annotation.as_json())
    module.exit_json(annotations=annotations, changed=changed)

main()
