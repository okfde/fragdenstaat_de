#!/usr/bin/env python3

import re

import requirements
import yaml

repos = {
    "froide": "froide",
    "froide-campaign": "froide_campaign",
    "froide-exam": "froide_exam",
    "froide-food": "froide_food",
    "froide-legalaction": "froide_legalaction",
    "froide-payment": "froide_payment",
    "django-filingcabinet": "@okfde/filingcabinet",
}

commit_re = r"tar\.gz\/([0-9a-f]*)"

with open("requirements.txt", "r") as requirements_fd:
    with open(file="pnpm-lock.yaml", mode="r") as pnpm_lock_fd:
        pnpm_lock = yaml.load(pnpm_lock_fd, yaml.SafeLoader)
        npm_packages = pnpm_lock["importers"]["."]["dependencies"]

        for req in requirements.parse(requirements_fd):
            if req.name in repos:
                npm_package_name = repos[req.name]

                if npm_package_name in npm_packages:
                    npm_package = npm_packages[npm_package_name]
                    requirements_version = req.revision

                    npm_version_re = re.search(commit_re, npm_package["version"])
                    assert npm_version_re is not None

                    npm_version = npm_version_re.group(1)
                    assert (
                        npm_version == requirements_version
                    ), f"{req.name} is on a different version in the requirements.txt than in the pnpm-lock.yaml. Run make sync_frontend_deps to fix this."
