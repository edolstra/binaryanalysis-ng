import sys, os
from test.TestUtil import *

from UnpackParserException import UnpackParserException
from .UnpackParser import GimpBrushUnpackParser

class TestGifUnpackParser(TestBase):
    def test_load_standard_gbr_file(self):
        rel_testfile = pathlib.Path('unpackers') / 'gimpbrush' / 'test.gbr'
        filename = pathlib.Path(self.testdata_dir) / rel_testfile
        self._copy_file_from_testdata(rel_testfile)
        fileresult = create_fileresult_for_path(self.unpackdir, rel_testfile,
                set())
        filesize = fileresult.filesize
        data_unpack_dir = rel_testfile.parent / 'some_dir'
        p = GimpBrushUnpackParser(fileresult, self.scan_environment,
                data_unpack_dir, 0)
        p.open()
        r = p.parse_and_unpack()
        p.close()
        self.assertTrue(r['status'])
        self.assertEqual(r['length'], filesize)
        self.assertEqual(r['filesandlabels'], [])
        self.assertEqual(r['metadata']['width'], 64)

    def test_load_offset_gbr_file(self):
        rel_testfile = pathlib.Path('unpackers') / 'gimpbrush' / 'test-prepend-random-data.gbr'
        filename = pathlib.Path(self.testdata_dir) / rel_testfile
        self._copy_file_from_testdata(rel_testfile)
        fileresult = create_fileresult_for_path(self.unpackdir, rel_testfile,
                set())
        filesize = fileresult.filesize
        data_unpack_dir = rel_testfile.parent / 'some_dir'
        offset = 128
        p = GimpBrushUnpackParser(fileresult, self.scan_environment,
                data_unpack_dir, offset)
        p.open()
        r = p.parse_and_unpack()
        p.close()
        self.assertTrue(r['status'])
        self.assertEqual(r['length'], filesize - offset)
        self.assertEqual(r['filesandlabels'], [])
        self.assertEqual(r['metadata']['width'], 64)

if __name__ == '__main__':
    unittest.main()

