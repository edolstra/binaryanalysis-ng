import os
import sys
import pathlib
import pytest
import shutil

from FileResult import *
from ScanEnvironment import *
from bangsignatures import maxsignaturesoffset
from .mock_queue import *
from .mock_db import *

_scriptdir = os.path.dirname(__file__)
testdir_base = pathlib.Path(_scriptdir).resolve()


@pytest.fixture(scope='module')
def scan_environment(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("bang")
    return ScanEnvironment(
        maxbytes = max(200000, maxsignaturesoffset+1),
        readsize = 10240,
        createbytecounter = False,
        createjson = True,
        runfilescans = True, # TODO: is this the correct value?
        tlshmaximum = sys.maxsize,
        synthesizedminimum = 10,
        logging = False,
        paddingname = 'PADDING',
        unpackdirectory = tmp_dir / 'unpack',
        temporarydirectory = tmp_dir / 'tmp',
        resultsdirectory = tmp_dir / 'results',
        scanfilequeue = MockQueue(),
        resultqueue = MockQueue(),
        processlock = MockLock(),
        checksumdict = {},
    )

def fileresult(basedir, rel_path, labels, calculate_size = True):
    parentlabels = set()
    parent = FileResult(None, rel_path.parent, parentlabels)
    fr = FileResult(parent, rel_path, labels)
    if calculate_size:
        fp = pathlib.Path(basedir) / rel_path
        fr.set_filesize(fp.stat().st_size)
    return fr

def copy_testfile_to_environment(basedir, rel_path, scan_environment):
    unpacked_path = scan_environment.unpackdirectory / rel_path
    try:
        os.makedirs(unpacked_path.parent)
    except FileExistsError:
        pass
    shutil.copy(basedir / rel_path, unpacked_path)

def create_unpackparser_for_path(scan_environment, testdata_dir, rel_testfile, unpackparser, offset,
        data_unpack_dir = pathlib.Path('.'), has_unpack_parent = False,
        calculate_size = True):
    """Creates an unpackparser of type unpackparser to unpack the file
    rel_testfile, starting at offset.
    data_unpack_dir is the path of the directory to which any files are
        extracted. The path is relative to the unpack root directory.
    has_unpack_parent indicates if this file is unpacked from another file.
        if True, rel_testfile is relative to the unpack root directory,
        if False, rel_testfile is relative to the testdata directory.
    calculate_size will calculate the size of the file. If the file does not
        exist for some reason, this flag can be set to False. Default is
        True.
    """
    # self._copy_file_from_testdata(rel_testfile)
    if has_unpack_parent:
        parent = FileResult(None, rel_testfile.parent, set())
        fileresult = FileResult(parent, rel_testfile, set())
    else:
        fileresult = FileResult(None, testdata_dir / rel_testfile, set())
    if calculate_size:
        path = scan_environment.get_unpack_path_for_fileresult(fileresult)
        fileresult.set_filesize(path.stat().st_size)
    p = unpackparser(fileresult, scan_environment, data_unpack_dir, offset)
    return p




def assertUnpackedPathExists(scan_environment, extracted_fn, message=None):
    extracted_fn_abs = pathlib.Path(scan_environment.unpackdirectory) / extracted_fn
    assert extracted_fn_abs.exists(), message

def assertUnpackedPathDoesNotExist(scan_environment, extracted_fn, message=None):
    extracted_fn_abs = pathlib.Path(scan_environment.unpackdirectory) / extracted_fn
    assert extracted_fn_abs.exists(), message

