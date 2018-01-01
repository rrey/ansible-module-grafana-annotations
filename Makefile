
syntax:
	pycodestyle --ignore=E265 library/grafana_annotations.py

check:
	tools/start_grafana.sh
	ansible-playbook test.yml
