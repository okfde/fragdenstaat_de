#!/usr/bin/env python3

import re
import tomllib

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

uv_commit_re = re.compile(r"#([0-9a-f]+)$")
pnpm_commit_re = re.compile(r"tar\.gz\/([0-9a-f]+)")

with (
    open("uv.lock", "rb") as uv_lock_fd,
    open(file="pnpm-lock.yaml", mode="r") as pnpm_lock_fd,
):
    pnpm_lock = yaml.load(pnpm_lock_fd, yaml.SafeLoader)
    npm_packages = pnpm_lock["importers"]["."]["dependencies"]

    uv_lock = tomllib.load(uv_lock_fd)
    uv_modules = uv_lock["package"]

    for python_module_name, npm_package_name in repos.items():
        python_module = next(
            p for p in uv_lock["package"] if p["name"] == python_module_name
        )
        assert python_module

        python_version = uv_commit_re.search(python_module["source"]["git"])
        assert python_version
        python_version = python_version.group(1)

        npm_version = pnpm_commit_re.search(npm_packages[npm_package_name]["version"])
        assert npm_version
        npm_version = npm_version.group(1)

        assert (
            npm_version == python_version
        ), f"{python_module_name} versions differ in uv.lock and pnpm-lock.yaml ({python_version[:8]} vs. {npm_version[:8]}). Run `make dependencies` to fix this."
