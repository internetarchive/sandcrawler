
SHELL=/bin/bash -euo pipefail
TODAY ?= $(shell date --iso --utc)
DATADIR ?= /srv/sandcrawler/tasks/$(TODAY)
DATESLUG ?= $(shell date +%Y-%m-%d.%H%M%S)
DATABASE_URL ?= sandcrawler

.PHONY: help
help: ## Print info about all commands
	@echo "Commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: create_datadir
create_datadir:
	mkdir -p $(DATADIR)/
	sudo chmod a+rw $(DATADIR)/

$(DATADIR)/.DB_DUMP:
	sudo -u postgres pg_dump --verbose --format=custom --exclude-table-data=crossref sandcrawler > $(DATADIR)/sandcrawler_${DATESLUG}.pgdump.wip
	mv $(DATADIR)/sandcrawler_${DATESLUG}.pgdump.wip $(DATADIR)/sandcrawler_${DATESLUG}.pgdump
	touch $@

.PHONY: database-snapshot
database-snapshot: create_datadir $(DATADIR)/.DB_DUMP ## Create SQL database snapshot
	@echo

$(DATADIR)/.DB_UPLOADED: $(DATADIR)/.DB_DUMP
	ia upload --checksum sandcrawler_sqldump_$(TODAY) ia_sqldump_item_readme.md --remote-name=README.md -m collection:webgroup-internal-backups -m mediatype:data -m creator:"Internet Archive Web Group" -m date:$(TODAY) -m title:"Sandcrawler SQL Database Snapshot ($(TODAY))"
	ia upload --checksum sandcrawler_sqldump_$(TODAY) $(DATADIR)/sandcrawler_*.pgdump
	touch $@

.PHONY: upload-database-snapshot
upload-database-snapshot: create_datadir database-snapshot $(DATADIR)/.DB_UPLOADED ## Upload database snapshot to archive.org
	@echo
