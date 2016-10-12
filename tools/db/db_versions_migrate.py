#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2012 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Utility for diff'ing two versions of the DB schema.

Each release cycle the plan is to compact all of the migrations from that
release into a single file. This is a manual and, unfortunately, error-prone
process. To ensure that the schema doesn't change, this tool can be used to
diff the compacted DB schema to the original, uncompacted form.

The database is specified by providing a SQLAlchemy connection URL WITHOUT the
database-name portion (that will be filled in automatically with a temporary
database name).

The schema versions are specified by providing a git ref (a branch name or
commit hash) and a SQLAlchemy-Migrate version number:

"""

from __future__ import print_function

import datetime
import os
import sys
import re
from datetime import datetime
import logging
import shutil

# Migrate
current_dir = os.getcwd()
current_dir = os.path.dirname(current_dir)
current_dir = os.path.dirname(current_dir)

MIGRATE_REPO = os.path.join(current_dir, "jacket", "db", "sqlalchemy",
                            "migrate_repo")
API_DB_MIGRATE_REPO = os.path.join(current_dir, "jacket", "db", "sqlalchemy",
                                   "api_migrations", "migrate_repo")
COMPUTE_MIGRATE_REPO = os.path.join(current_dir, "jacket", "db", "compute",
                                    "sqlalchemy", "migrate_repo")
STORAGE_MIGRATE_REPO = os.path.join(current_dir, "jacket", "db", "storage",
                                    "sqlalchemy", "migrate_repo")
EXTEND_MIGRATE_REPO = os.path.join(current_dir, "jacket", "db", "extend",
                                         "sqlalchemy", "migrate_repo")
COMPUTE_API_DB_MIGRATE_REPO = os.path.join(current_dir, "jacket", "db",
                                           "compute", "sqlalchemy",
                                           "api_migrations", "migrate_repo")

MODELS = {"compute": COMPUTE_MIGRATE_REPO,
          "storage": STORAGE_MIGRATE_REPO,
          "extend": EXTEND_MIGRATE_REPO,}

log = logging.getLogger(__name__)


class VerNum(object):
    """A version number that behaves like a string and int at the same time"""

    _instances = dict()

    def __new__(cls, value):
        val = str(value)
        if val not in cls._instances:
            cls._instances[val] = super(VerNum, cls).__new__(cls)
        ret = cls._instances[val]
        return ret

    def __init__(self, value):
        self.value = str(int(value))
        if self < 0:
            raise ValueError("Version number cannot be negative")

    def __add__(self, value):
        ret = int(self) + int(value)
        return VerNum(ret)

    def __sub__(self, value):
        return self + (int(value) * -1)

    def __eq__(self, value):
        return int(self) == int(value)

    def __ne__(self, value):
        return int(self) != int(value)

    def __lt__(self, value):
        return int(self) < int(value)

    def __gt__(self, value):
        return int(self) > int(value)

    def __ge__(self, value):
        return int(self) >= int(value)

    def __le__(self, value):
        return int(self) <= int(value)

    def __repr__(self):
        return "<VerNum(%s)>" % self.value

    def __str__(self):
        return str(self.value)

    def __int__(self):
        return int(self.value)

    def __index__(self):
        return int(self.value)


class Collection(object):
    """A collection of versioning scripts in a repository"""

    FILENAME_WITH_VERSION = re.compile(r'^(\d{3,}).*')

    def __init__(self, path):
        """Collect current version scripts in repository
        and store them in self.versions
        """

        # Create temporary list of files, allowing skipped version numbers.
        self.path = path
        files = os.listdir(path)
        if '1' in files:
            # deprecation
            raise Exception('It looks like you have a repository in the old '
                            'format (with directories for each version). '
                            'Please convert repository before proceeding.')

        tempVersions = dict()
        for filename in files:
            match = self.FILENAME_WITH_VERSION.match(filename)
            if match:
                num = int(match.group(1))
                tempVersions.setdefault(num, []).append(filename)
            else:
                pass  # Must be a helper file or something, let's ignore it.

        # Create the versions member where the keys
        # are VerNum's and the values are Version's.
        self.versions = dict()
        for num, files in tempVersions.items():
            self.versions[VerNum(num)] = Version(num, path, files)

    def parse_model(self, model):
        model_versions = {}
        for num, version in self.versions.iteritems():
            file_num, file_path, parent_path = version.parse_model(model)
            if file_num is not None and file_path is not None:
                model_versions[file_num] = {'parent_num': num,
                                            'path': file_path,
                                            'version': version}
        return model_versions

    @property
    def latest(self):
        """:returns: Latest version in Collection"""
        return max([VerNum(0)] + list(self.versions.keys()))

    def _next_ver_num(self, use_timestamp_numbering):
        if use_timestamp_numbering == True:
            return VerNum(int(datetime.utcnow().strftime('%Y%m%d%H%M%S')))
        else:
            return self.latest + 1

    def version(self, vernum=None):
        """Returns latest Version if vernum is not given.
        Otherwise, returns wanted version"""
        if vernum is None:
            vernum = self.latest
        return self.versions[VerNum(vernum)]

    @classmethod
    def clear(cls):
        super(Collection, cls).clear()

    def _version_path(self, ver):
        """Returns path of file in versions repository"""
        return os.path.join(self.path, str(ver))


class Version(object):
    """A single version in a collection
    :param vernum: Version Number
    :param path: Path to script files
    :param filelist: List of scripts
    :type vernum: int, VerNum
    :type path: string
    :type filelist: list
    """

    def __init__(self, vernum, path, filelist):
        self.version = VerNum(vernum)

        # Collect scripts in this folder
        self.python = None

        for script in filelist:
            self.add_script(os.path.join(path, script))

    def add_script(self, path):
        """Add script to Collection/Version"""
        if path.endswith(Extensions.py):
            self._add_script_py(path)

    def _add_script_py(self, path):
        if self.python is not None:
            raise Exception('You can only have one Python script '
                            'per version, but you have: %s and %s' % (
                            self.python, path))
        self.python = path

    def parse_model(self, model):
        filename = os.path.basename(self.python)
        file_split = filename.split('_', 3)
        if len(file_split) < 4:
            return None, None, None
        if file_split[1] != model:
            return None, None, None

        num = file_split[2]
        file_path = filename.split('_', 2)[2]

        return num, file_path, self.python


class Extensions(object):
    """A namespace for file extensions"""
    py = 'py'
    sql = 'sql'


def str_to_filename(s):
    """Replaces spaces, (double and single) quotes
    and double underscores to underscores
    """

    s = s.replace(' ', '_').replace('"', '_').replace("'", '_').replace(".",
                                                                        "_")
    while '__' in s:
        s = s.replace('__', '_')
    return s


# Command
def die(msg):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(1)


def usage(msg=None):
    if msg:
        print("ERROR: %s" % msg, file=sys.stderr)

    prog = "db_versions_migrate.py"
    args = []

    print("usage: %s %s" % (prog, ' '.join(args)), file=sys.stderr)
    sys.exit(1)


def model_process(model, dest_versions, latest):
    model_coll = Collection(os.path.join(MODELS[model], "versions"))

    temp_versions = dest_versions.parse_model(model)
    temp_keys = temp_versions.keys()
    model_versions = sorted(model_coll.versions.iteritems(), key=lambda x: x[0])

    for cur_num, curl_version in model_versions:
        latest_num = latest + 1
        if temp_keys:
            if cur_num in temp_keys:
                num_str = "%03d" % int(cur_num)
                parent_version = temp_versions[num_str]['version']
                parent_num = temp_versions[num_str]['parent_num']
                os.remove(parent_version.python)
                latest_num = parent_num
            else:
                latest += 1
        else:
            latest += 1

        dest_file_name = "%03d_%s_%s" % (
        int(latest_num), model, os.path.basename(curl_version.python))
        dest_path = os.path.join(dest_versions.path, dest_file_name)
        src_path = os.path.join(model_coll.path,
                                os.path.basename(curl_version.python))
        shutil.copyfile(src_path, dest_path)

    return latest


def main():
    # timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print("main start....")
    db_versions_path = os.path.join(MIGRATE_REPO, "versions")

    db_versions = Collection(db_versions_path)
    latest = db_versions.latest
    latest = model_process('compute', db_versions, latest)
    latest = model_process('storage', db_versions, latest)
    latest = model_process('hybridcloud', db_versions, latest)

    # api db
    compute_api_db_versions_path = os.path.join(COMPUTE_API_DB_MIGRATE_REPO,
                                                "versions")
    api_db_versions_path = os.path.join(API_DB_MIGRATE_REPO, "versions")

    shutil.rmtree(api_db_versions_path)
    shutil.copytree(compute_api_db_versions_path, api_db_versions_path)


if __name__ == "__main__":
    print("start....")
    main()
    print("end....")
    sys.exit(0)
