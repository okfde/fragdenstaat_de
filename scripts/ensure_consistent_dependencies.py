#!/usr/bin/env python3

import re
import sys

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

pip_commit_re = r"^(.*) @ git.*@([0-9a-f]*)"
pnpm_commit_re = r"tar\.gz\/([0-9a-f]*)"

failed = False
with open("requirements.txt", "r") as requirements_fd:
    with open(file="pnpm-lock.yaml", mode="r") as pnpm_lock_fd:
        pnpm_lock = yaml.load(pnpm_lock_fd, yaml.SafeLoader)
        npm_packages = pnpm_lock["importers"]["."]["dependencies"]

        for match in re.finditer(pip_commit_re, requirements_fd.read(), re.MULTILINE):
            req_name = match.group(1)
            req_version = match.group(2)

            if req_name in repos:
                npm_package_name = repos[req_name]

                if npm_package_name in npm_packages:
                    npm_package = npm_packages[npm_package_name]
                    requirements_version = req_version

                    npm_version_re = re.search(pnpm_commit_re, npm_package["version"])
                    assert npm_version_re is not None, npm_package["version"]

                    npm_version = npm_version_re.group(1)
                    if npm_version != requirements_version:
                        print(
                            f"{req_name} is on a different version in the requirements.txt than in the pnpm-lock.yaml. Run `make dependencies` to fix this. ({npm_version} vs {requirements_version})"
                        )
                        failed = True

if failed:
    sys.exit(1)
