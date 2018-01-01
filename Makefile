
syntax:
	pycodestyle --ignore=E265 library/grafana_annotations.py

container:
	tools/start_grafana.sh

check: container
	GRAFANA_API_TOKEN='$(shell python tools/get_or_create_token.py)' ansible-playbook test.yml
