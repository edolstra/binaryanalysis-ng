import sys, os
from test.TestUtil import *
from UnpackParserException import UnpackParserException

from .UnpackParser import MbrPartitionTableUnpackParser

class TestMbrPartitionTableUnpackParser(TestBase):
    def test_load_standard_file(self):
        rel_testfile = pathlib.Path('a') / \
            'openwrt-18.06.1-brcm2708-bcm2710-rpi-3-ext4-sysupgrade.img'
        p = self.create_unpackparser_for_path(rel_testfile,
                MbrPartitionTableUnpackParser, 0)
        p.open()
        r = p.parse_and_unpack()
        p.close()
        self.assertEqual(r.get_length(), self.get_testfile_size(rel_testfile))
        self.assertEqual(len(r.get_unpacked_files()), 4)

    def test_load_fat_partition(self):
        rel_testfile = pathlib.Path('unpackers') / 'fat' / 'test.fat'
        p = self.create_unpackparser_for_path(rel_testfile,
                MbrPartitionTableUnpackParser, 0)
        p.open()
        with self.assertRaisesRegex(UnpackParserException, r"no partitions") as cm:
            r = p.parse_and_unpack()
        p.close()

    def test_load_gpt_partition_table(self):
        rel_testfile = pathlib.Path('a') / 'OPNsense-18.1.6-OpenSSL-vga-amd64.img'
        p = self.create_unpackparser_for_path(rel_testfile,
                MbrPartitionTableUnpackParser, 0)
        p.open()
        with self.assertRaisesRegex(UnpackParserException,
                r"partition bigger than file") as cm:
            r = p.parse_and_unpack()
        p.close()


if __name__ == '__main__':
    unittest.main()

