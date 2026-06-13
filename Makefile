PYTHONPATH := services/fraud_platform/src
PYTHON := python3

.PHONY: bootstrap prereqs data train reset-demo up stream-demo demo-ui api react-ui test deploy-aws

bootstrap:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[api,tracking,streaming,model,cloud]"

prereqs:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.cli check-prereqs

data:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.cli make-sample-data

train:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.cli train --source auto

reset-demo:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.cli reset-state

up:
	docker compose -f infra/docker/docker-compose.yml up --build

stream-demo:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.cli stream-demo --events 120 --sleep 0.05 --inject-drift-after 70 --reset-state

demo-ui:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) apps/python_dashboard/server.py

api:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m fraud_platform.api.server

react-ui:
	cd apps/react_dashboard && npm install && npm run dev

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

deploy-aws:
	cd infra/terraform && terraform init && terraform apply
