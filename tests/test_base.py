import pytest
import os
import subprocess
import json
import time


class TestClass(object):

    # {{{ call module
    def _run_module(self, json_args):
        with open("/tmp/test.json", "w+") as jsonfile:
            json.dump(json_args, jsonfile)
        args = ["python", "%s/library/grafana_annotations.py" % os.getenv("BASEDIR"), "/tmp/test.json"]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        return p.returncode, p.stdout.read(), p.stderr.read()
    # }}}

    def test_basic(self):
        module_args = {
            "ANSIBLE_MODULE_ARGS": {
                "text": "This is pytest basic test without time value",
                "url": "http://127.0.0.1:3000/api/annotations",
                "url_password": "admin",
                "url_username": "admin",
                "_ansible_remote_tmp": "/tmp",
                "_ansible_keep_remote_files": "false"
            }
        }
        rc, stdout, stderr = self._run_module(module_args)
        assert rc == 0, stderr
        ouput_json = json.loads(stdout)
        assert ouput_json.get("changed") is True

    def test_explicit_time(self):
        current_time = int(time.time())
        module_args = {
            "ANSIBLE_MODULE_ARGS": {
                "text": "This is pytest basic test with explicit time value",
                "url": "http://127.0.0.1:3000/api/annotations",
                "url_password": "admin",
                "url_username": "admin",
                "time": str(current_time),
                "_ansible_remote_tmp": "/tmp",
                "_ansible_keep_remote_files": "false"
            }
        }
        rc, stdout, stderr = self._run_module(module_args)
        assert rc == 0, stderr
        ouput_json = json.loads(stdout)
        assert ouput_json.get("changed") is True, ouput_json

    def test_idempotency(self):
        current_time = int(time.time())
        module_args = {
            "ANSIBLE_MODULE_ARGS": {
                "text": "This is pytest basic test for idempotency",
                "url": "http://127.0.0.1:3000/api/annotations",
                "url_password": "admin",
                "url_username": "admin",
                "time": str(current_time),
                "_ansible_remote_tmp": "/tmp",
                "_ansible_keep_remote_files": "false"
            }
        }
        # {{{ send the annotation once
        rc, stdout, stderr = self._run_module(module_args)
        assert rc == 0, stderr
        ouput_json = json.loads(stdout)
        assert ouput_json.get("changed") is True, ouput_json
        # }}}
        # send the annotation again
        rc, stdout, stderr = self._run_module(module_args)
        assert rc == 0, stderr
        ouput_json = json.loads(stdout)
        assert ouput_json.get("changed") is False, ouput_json
