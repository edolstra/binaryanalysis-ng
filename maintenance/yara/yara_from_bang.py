#!/usr/bin/env python3

# Binary Analysis Next Generation (BANG!)
#
# Copyright 2021 - Armijn Hemel
# Licensed under the terms of the GNU Affero General Public License version 3
# SPDX-License-Identifier: AGPL-3.0-only

'''
This script processes BANG results and generates YARA rules
'''

import sys
import os
import argparse
import pathlib
import tempfile
import shutil
import hashlib
import subprocess
import shutil
import datetime
import pickle
import re
import uuid

import packageurl

# import YAML module for the configuration
from yaml import load
from yaml import YAMLError
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

def normalize_name(name):
    for i in ['.', '-']:
        if i in name:
            name = name.replace(i, '_')
    return name

def generate_yara_package(yara_directory, package_name, functions, variables, strings):
    # open a rule
    generate_date = datetime.datetime.utcnow().isoformat()
    rule_uuid = uuid.uuid4()
    meta = '''
    meta:
        description = "Rule for %s"
        author = "Generated by BANG"
        package_name = "%s"
        date = "%s"
        uuid = "%s"
''' % (package_name, package_name, generate_date, rule_uuid)

    yara_file = yara_directory / ("%s.yara" % package_name)
    rule_name = 'rule rule_%s\n' % normalize_name(str(rule_uuid))
    generate_yara(yara_file, rule_name, meta, functions, variables,strings)
    return yara_file.name

def generate_yara_binary(yara_directory, package_name, binary, functions, variables, strings):
    generate_date = datetime.datetime.utcnow().isoformat()
    rule_uuid = uuid.uuid4()
    meta = '''
    meta:
        description = "Rule for %s in %s"
        author = "Generated by BANG"
        package_name = "%s"
        binary_name = "%s"
        date = "%s"
        uuid = "%s"
''' % (binary, package_name, package_name, binary, generate_date, rule_uuid)

    yara_file = yara_directory / ("%s-%s.yara" % (package_name, binary))
    rule_name = 'rule rule_%s\n' % normalize_name(str(rule_uuid))
    generate_yara(yara_file, rule_name, meta, functions, variables,strings)
    return yara_file.name

def generate_yara(yara_file, rule_name, meta, functions, variables, strings):
    # open a rule
    with yara_file.open(mode='w') as p:
        #p.write('rule %s\n' % package_name)
        p.write(rule_name)
        p.write('{')
        p.write(meta)
        p.write('\n    strings:\n')

        # write the strings
        counter = 1
        p.write("\n        // Extracted strings\n\n")
        for s in sorted(strings):
            # TODO: properly escape characters
            p.write("        $string%d = \"%s\"\n" % (counter, s))
            counter += 1

        # write the functions
        p.write("\n        // Extracted functions\n\n")
        counter = 1
        for s in sorted(functions):
            p.write("        $function%d = \"%s\"\n" % (counter, s))
            counter += 1

        # write the variable names
        p.write("\n        // Extracted variables\n\n")
        counter = 1
        for s in sorted(variables):
            p.write("        $variable%d = \"%s\"\n" % (counter, s))
            counter += 1

        # TODO: find good heuristics of how many identifiers should be matched
        p.write('\n    condition:\n')
        p.write('        all of them\n')
        p.write('\n}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", action="store", dest="cfg",
                        help="path to configuration file", metavar="FILE")
    parser.add_argument("-r", "--result-directory", action="store", dest="result_directory",
                        help="path to BANG result directories", metavar="DIR")
    args = parser.parse_args()

    # sanity checks for the configuration file
    if args.cfg is None:
        parser.error("No configuration file provided, exiting")

    cfg = pathlib.Path(args.cfg)

    # the configuration file should exist ...
    if not cfg.exists():
        parser.error("File %s does not exist, exiting." % args.cfg)

    # ... and should be a real file
    if not cfg.is_file():
        parser.error("%s is not a regular file, exiting." % args.cfg)

    # sanity checks for the result directory
    if args.result_directory is None:
        parser.error("No result directory provided, exiting")

    result_directory = pathlib.Path(args.result_directory)

    # the result directory should exist ...
    if not result_directory.exists():
        parser.error("File %s does not exist, exiting." % args.result_directory)

    # ... and should be a real directory
    if not result_directory.is_dir():
        parser.error("%s is not a directory, exiting." % args.result_directory)

    # read the configuration file. This is in YAML format
    try:
        configfile = open(args.cfg, 'r')
        config = load(configfile, Loader=Loader)
    except (YAMLError, PermissionError):
        print("Cannot open configuration file, exiting", file=sys.stderr)
        sys.exit(1)

    # some sanity checks:
    #for i in ['database', 'general', 'yara']:
    for i in ['general', 'yara']:
        if i not in config:
            print("Invalid configuration file, section %s missing, exiting" % i,
                  file=sys.stderr)
            sys.exit(1)

    verbose = False
    if 'verbose' in config['general']:
        if isinstance(config['general']['verbose'], bool):
            verbose = config['general']['verbose']

    if 'yara_directory' not in config['yara']:
        print("yara_directory not defined in configuration, exiting",
              file=sys.stderr)
        sys.exit(1)

    yara_directory = pathlib.Path(config['yara']['yara_directory'])
    if not yara_directory.exists():
        print("yara_directory does not exist, exiting",
              file=sys.stderr)
        sys.exit(1)

    if not yara_directory.is_dir():
        print("yara_directory is not a valid directory, exiting",
              file=sys.stderr)
        sys.exit(1)

    # check if the yara directory is writable
    try:
        temp_name = tempfile.NamedTemporaryFile(dir=yara_directory)
        temp_name.close()
    except:
        print("yara_directory is not writable, exiting",
              file=sys.stderr)
        sys.exit(1)

    yara_package_directory = yara_directory / 'package'
    yara_binary_directory = yara_directory / 'binary'

    yara_package_directory.mkdir(exist_ok=True)
    yara_binary_directory.mkdir(exist_ok=True)

    string_cutoff = 8
    if 'string_cutoff' in config['yara']:
        if type(config['yara']['string_cutoff']) == int:
            string_cutoff = config['yara']['string_cutoff']

    # walk the results directory
    for bang_directory in result_directory.iterdir():
        bang_pickle = bang_directory / 'bang.pickle'
        if not bang_pickle.exists():
            continue

        functions_per_package = set()
        variables_per_package = set()
        strings_per_package = set()

        elf_to_identifiers = {}

        # open the top level pickle
        bang_data = pickle.load(open(bang_pickle, 'rb'))
        package_name = ''
        for bang_file in bang_data['scantree']:
            if 'root' in bang_data['scantree'][bang_file]['labels']:
                package_name = pathlib.Path(bang_file).name
            if 'elf' in bang_data['scantree'][bang_file]['labels']:
                sha256 = bang_data['scantree'][bang_file]['hash']['sha256']
                elf_name = pathlib.Path(bang_file).name

                # open the result pickle
                try:
                    results_data = pickle.load(open(bang_directory / 'results' / ("%s.pickle" % sha256), 'rb'))
                except:
                    continue
                if 'metadata' not in results_data:
                    # example: statically linked binaries currently
                    # have no associated metadata.
                    continue
                strings = set()
                functions = set()
                variables = set()
                if results_data['metadata']['strings'] != []:
                    for s in results_data['metadata']['strings']:
                        if len(s) < string_cutoff:
                            continue
                        # ignore whitespace-only strings
                        if re.match('^\s+$', s) is None:
                            strings.add(s)
                    strings_per_package.update(strings)
                if results_data['metadata']['symbols'] != []:
                    for s in results_data['metadata']['symbols']:
                        if s['section_index'] == 0:
                            continue
                        if s['type'] == 'func':
                            functions.add(s['name'])
                        elif s['type'] == 'object':
                            variables.add(s['name'])
                    functions_per_package.update(functions)
                    variables_per_package.update(variables)
                if elf_name not in elf_to_identifiers:
                    elf_to_identifiers['strings'] = strings
                    elf_to_identifiers['variables'] = variables
                    elf_to_identifiers['functions'] = functions
                yara_name = generate_yara_binary(yara_binary_directory, package_name, elf_name, functions, variables, strings)
        if strings_per_package == set() and variables_per_package == set() and functions_per_package == set():
            continue
    
        yara_name = generate_yara_package(yara_package_directory, package_name, functions_per_package, variables_per_package, strings_per_package)

if __name__ == "__main__":
    main()
