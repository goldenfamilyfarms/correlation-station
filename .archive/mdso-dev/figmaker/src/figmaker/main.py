#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright(c) 2020, Ciena All rights reserved.
from jinja2 import Template
import json
import argparse
from os import environ
import figmaker
import pkg_resources
from os.path import join
import os
import git
import re


def get_version_json(path):
    with open(path) as f:
        data = json.load(f)
    f.close
    return data


def calculate_image_tag(argv=None, args=None):
    if (args is None):
        args = get_args(argv)

    data = get_version_json(args.version_json)

    if "CI_COMMIT_SHORT_SHA" in os.environ:
        sha = environ.get('CI_COMMIT_SHORT_SHA')
    else:
        repo = git.Repo(os.getcwd(), search_parent_directories=True)
        sha = repo.head.commit.hexsha[0: 8]
    pipelineiid = environ.get('CI_PIPELINE_IID', 'NO_PIPELINEIID')
    pipelineid = environ.get('CI_PIPELINE_ID', 'NO_PIPELINEID')

    version = data['version']
    semver = version
    semver_mdso = "%s.%s" % (version, data['mdso_version'])
    semver_mdso_sha = "%s.%s" % (semver_mdso, sha)
    semver_mdso_pipelineid = "%s.%s" % (semver_mdso, pipelineid)
    semver_mdso_pipelineid_sha = "%s.%s" % (semver_mdso_pipelineid, sha)
    semver_mdso_sha_pipelineiid = "%s.%s" % (semver_mdso_sha, pipelineiid)
    if (args.tag_type == 'semver'):
        result = semver
    elif (args.tag_type == 'semver_mdso'):
        result = semver_mdso
    elif (args.tag_type == 'semver_mdso_sha'):
        result = semver_mdso_sha
    elif (args.tag_type == 'semver_mdso_sha_pipelineiid'):
        result = semver_mdso_sha_pipelineiid
    elif (args.tag_type == 'semver_mdso_pipelineid_sha'):
        result = semver_mdso_pipelineid_sha
    else:
        result = "unknown"
    return result


def get_image_tag(argv=None, args=None):
    result = calculate_image_tag(argv=argv, args=args)
    print(result)


def get_image_vendor(argv=None, args=None):
    if (args is None):
        args = get_args(argv)
    if (args.registry == 'artifactory'):
        data = get_artifactory_paths()
        result = data['vendor']
    if (args.registry == 'blueplanet'):
        data = get_blueplanet_paths()
        result = data['vendor']
    print(result)


def get_artifactory_paths(data={}):
    result = data
    result['registry'] = "artifactory.ciena.com"
    result['vendor'] = "blueplanet"
    return result


def get_blueplanet_paths(data={}):
    result = data

    if "CI_REGISTRY_IMAGE" in os.environ:
        result['registry'] = "registry.blueplanet.com"
        result['vendor'] = environ.get('CI_REGISTRY_IMAGE').replace('registry.blueplanet.com/', '')
    else:
        # attempt to determine image path from git remote
        try:
            repo = git.Repo(os.getcwd(), search_parent_directories=True)
            remote_url = repo.remotes.origin.url
            if (remote_url.find("git.blueplanet.com") > 0):
                replacement = re.sub(r"git@git", "registry", remote_url)
                replacement = re.sub(r"https\:\/\/git", "registry", replacement)
                replacement = re.sub(r":", "/", replacement)
                replacement = re.sub(r".git", "", replacement).lower()
                result['registry'] = "registry.blueplanet.com"
                result['vendor'] = replacement.replace('registry.blueplanet.com/', '')
        except AttributeError:
            result['vendor'] = "local_vendor"
            result['registry'] = "local_registry"
        except Exception:
            raise

    return result


def get_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('-i', dest='version_json', type=str, default='version.json',
                        help='path to version.json file to use')
    parser.add_argument('-r', dest='registry', type=str, default='blueplanet',
                        help='registry to use', choices=['artifactory', 'blueplanet'])
    parser.add_argument('-o', dest='output', type=str, default=None,
                        help='Filename to write to (default stdout)')
    parser.add_argument('-t', dest='tag_type', type=str, help='Tag type for the solution image',
                        default='semver_mdso_sha_pipelineiid',
                        choices=['semver', 'semver_mdso', 'semver_mdso_sha', 'semver_mdso_sha_pipelineiid', 'semver_mdso_pipelineid_sha'])
    parser.add_argument('--version', '-v', action='version', version=figmaker.__version__)
    args = parser.parse_args(argv)
    return args


def main(argv=None):
    args = get_args(argv)
    version = calculate_image_tag(args=args)
    data = get_version_json(args.version_json)
    data['version'] = version
    fig_j2 = pkg_resources.resource_string(__name__, "fig.j2").decode('utf-8')
    template = Template(fig_j2)

    if (args.registry == 'artifactory'):
        data = get_artifactory_paths(data)
    if (args.registry == 'blueplanet'):
        data = get_blueplanet_paths(data)

    result = template.render(data)

    if (args.output is not None):
        text_file = open(join(os.getcwd(), args.output), "wt")
        text_file.write(result)
        text_file.close()
    else:
        return result


if __name__ == '__main__':
    main()
