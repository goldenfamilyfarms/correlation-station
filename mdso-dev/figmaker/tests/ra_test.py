from figmaker.main import get_blueplanet_paths
from figmaker.main import main
from figmaker.main import get_artifactory_paths
from figmaker.main import calculate_image_tag
from os.path import dirname, join
import git
import os
import yaml
from os import environ

REPO = git.Repo(os.getcwd())
SHA = REPO.head.commit.hexsha[0: 8]


def test_get_blueplanet_paths():
    ras = {
        "name": "test"
    }
    val = get_blueplanet_paths(ras)
    assert val == {'name': 'test', 'registry': 'registry.blueplanet.com', 'vendor': 'blueplanet/devtools/figmaker'}


def test_get_artifactory_paths():
    ras = {
        "name": "test"
    }
    val = get_artifactory_paths(ras)
    assert val == {'name': 'test', 'registry': 'artifactory.ciena.com', 'vendor': 'blueplanet'}


def test_calculate_image_tag():
    pipelineiid = environ.get('CI_PIPELINE_IID', 'NO_PIPELINEIID')
    pipelineid = environ.get('CI_PIPELINE_ID', 'NO_PIPELINEID')
    val = calculate_image_tag(['-t', 'semver_mdso', '-i', 'tests/ra.json'])
    assert val == '1.1.1.1902'
    val = calculate_image_tag(['-t', 'semver_mdso_sha', '-i', 'tests/ra.json'])
    assert val == '1.1.1.1902.' + SHA
    val = calculate_image_tag(['-t', 'semver_mdso_sha_pipelineiid', '-i', 'tests/ra.json'])
    assert val == '1.1.1.1902.' + SHA + '.' + pipelineiid
    val = calculate_image_tag(['-t', 'semver_mdso_pipelineid_sha', '-i', 'tests/ra.json'])
    assert val == '1.1.1.1902.' + pipelineid + '.' + SHA


def test_main_ra():
    setup_dir = dirname(__file__)
    ra_path = join(setup_dir, 'ra.json')
    val = main(['-r', 'artifactory', '-i', ra_path, '-t', 'semver_mdso_sha'])
    data = yaml.load(val, Loader=yaml.FullLoader)

    assert data == {
        '__version__': 1,
        'solution_name': 'test',
        'solution_version': '1.1.1.1902.' + SHA,
        "apps": {
            "test": {
                "image": 'artifactory.ciena.com/blueplanet/test:1.1.1.1902.' + SHA,
                "max_instances": 1,
                "volumes": [
                    "/dev/log:/dev/log",
                    "/etc/hostname:/etc/physical_hostname:ro"
                ],
                "environment": ["BP2RemoveDataOnRestore=true"]
            }
        }
    }


def test_main_ra_no_volumes():
    setup_dir = dirname(__file__)
    ra_path = join(setup_dir, 'ra_no_volumes.json')
    val = main(['-r', 'artifactory', '-i', ra_path, '-t', 'semver_mdso_sha'])
    data = yaml.load(val, Loader=yaml.FullLoader)

    assert data == {
        '__version__': 1,
        'solution_name': 'test',
        'solution_version': '1.1.1.1902.' + SHA,
        "apps": {
            "test": {
                "image": 'artifactory.ciena.com/blueplanet/test:1.1.1.1902.' + SHA,
                "max_instances": 1,
                "volumes": [
                    "/dev/log:/dev/log",
                    '/etc/hostname:/etc/physical_hostname:ro'
                ],
                "environment": ["BP2RemoveDataOnRestore=true"]
            }
        }
    }


def test_main_ra_minimal():
    setup_dir = dirname(__file__)
    ra_path = join(setup_dir, 'ra_minimal.json')
    val = main(['-r', 'artifactory', '-i', ra_path, '-t', 'semver_mdso_sha'])
    data = yaml.load(val, Loader=yaml.FullLoader)

    assert data == {
        '__version__': 1,
        'solution_name': 'slackra',
        'solution_version': '1.0.9.1906.' + SHA,
        "apps": {
            "slackra": {
                "image": 'artifactory.ciena.com/blueplanet/slackra:1.0.9.1906.' + SHA,
                "max_instances": 1,
                "volumes": [
                    "/dev/log:/dev/log",
                    '/etc/hostname:/etc/physical_hostname:ro'
                ],
                "environment": ["BP2RemoveDataOnRestore=true"]
            }
        }
    }
