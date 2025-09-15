# JITX makefile for jitxlib Sphinx documentation
#

SHELL := /bin/bash

# You can set these variables from the command line, and also
# from the environment for the first three.
PIPOPTS       ?= --extra-index-url "https://pypi.jitx.com/jitx/main/+simple"
SPHINXOPTS    ?= --jobs 1 --write-all --fresh-env --warning-file build.out
SPHINXAPIDOC  ?= sphinx-apidoc
SPHINXBUILD   ?= sphinx-build
PROJNAME      := voltage-divider
SOURCEDIR     := source
BUILDDIR      := build
PYSRCDIR      := ../src/jitxlib
VER           := $(shell hatch version)
ARCHIVENAME   := docs-jitxlib-$(PROJNAME)-$(VER).tar.bz2

.PHONY: all
all: html archive

# create python venv
.venv: requirements.txt
	python -m venv .venv \
	  && source .venv/bin/activate \
	  && pip install $(PIPOPTS) -r requirements.txt \
	  && touch .venv

# generate docs from python source
.PHONY: apidoc
apidoc: .venv
	source .venv/bin/activate \
	  && $(SPHINXAPIDOC)  \
	    -o "source/jitxlib/$(PROJNAME)"  \
	    "../src/$(PYSRCDIR)"  \
	    --maxdepth 4  \
	    --separate  \
	    --implicit-namespaces  \
	    --doc-project "JITX $(PROJNAME) Documentation"

# convert to html
.PHONY: html
html: .venv apidoc
	source .venv/bin/activate \
	  && $(SPHINXBUILD) --builder html $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)"

# create archive
.PHONY: archive
archive:
	tar jcf "$(ARCHIVENAME)" "$(SOURCEDIR)" "$(BUILDDIR)"

# clean up
.PHONY: clean
clean:
	rm -rf .venv "source/jitxlib" "$(BUILDDIR)" build.out "$(ARCHIVENAME)"
