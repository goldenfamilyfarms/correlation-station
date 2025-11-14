#
# Module: Makefile
#
# Copyright(c) 2019, Ciena, Inc. All rights reserved.
#

VENDOR := $(shell cat version.json | jq -r .vendor)
VERSION := $(shell cat version.json | jq -r .version).dev.$(shell date +"%Y%m%d%H%M%S")
PACKAGE := $(shell cat version.json | jq -r .name)
REGISTRY := $(shell cat version.json | jq -r .registry)

# Markers to operate dependencies
JINJA2 := /usr/local/bin/jinja2

HIDE := @

$(JINJA2):
	$(HIDE)pip install jinja2-cli jinja2

image:
	$(HIDE)docker build -t $(VENDOR)/$(PACKAGE) .
	$(HIDE)docker tag $(VENDOR)/$(PACKAGE):latest $(REGISTRY)/$(VENDOR)/$(PACKAGE):$(VERSION)

push:
	$(HIDE)docker push $(REGISTRY)/$(VENDOR)/$(PACKAGE):$(VERSION)

solution: $(JINJA2)
	$(HIDE)cat version.json | jq .name=\"charter_sensor_templates\" > version1.json
	$(HIDE)cat version1.json | jq .image_version=\"$(VERSION)\" > version2.json
	$(HIDE)jinja2 fig.j2 version2.json > fig.yml
	$(HIDE)solmaker build --registry=$(REGISTRY) --vendor=$(VENDOR) --tag=$(VERSION) fig.yml
