#!/bin/python3
from pyhocon import ConfigFactory
from argparse import ArgumentParser
import sys
import glob


def main():
    parser = ArgumentParser()
    parser.add_argument("-t", "--tosca_file", help="Tosca file")
    parser.add_argument("-m", "--model-def", help="model-definitions dir")
    args = parser.parse_args()
    files = []
    if args.tosca_file:
        files.append(args.tosca_file)
    else:
        files = glob.glob("{}/**/*.tosca".format(args.model_def), recursive=True)

    flagged_sts = {}

    for file in files:
        conf = ConfigFactory.parse_file(file)
        legacy_plans = []

        if 'serviceTemplates' in conf:
            for st in conf['serviceTemplates']:
                if 'plans' in conf['serviceTemplates.{}'.format(st)]:
                    for plan in conf['serviceTemplates.{}.plans'.format(st)]:
                        script_type = conf['serviceTemplates.{}.plans.{}.type'.format(st, plan)]

                        if script_type == "script":
                            legacy_plans.append(plan)

            if legacy_plans:
                # warnings.error("{} has legacy scripts: {}".format(file, legacy_plans))
                print("{} has legacy scripts: {}".format(file, legacy_plans))
                flagged_sts[file] = legacy_plans

    if flagged_sts:
        sys.exit(1)


if __name__ == '__main__':
    main()
