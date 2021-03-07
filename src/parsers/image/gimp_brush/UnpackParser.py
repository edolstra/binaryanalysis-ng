import os
from UnpackParser import UnpackParser, check_condition
from UnpackParserException import UnpackParserException
from kaitaistruct import ValidationNotEqualError
from . import gimp_brush

from PIL.GbrImagePlugin import GbrImageFile

'''
class GimpBrushUnpackParserOld(WrappedUnpackParser):
    extensions = []
    signatures = [
        (20, b'GIMP')
    ]
    pretty_name = 'gimpbrush'

    def unpack_function(self, fileresult, scan_environment, offset, unpack_dir):
        return unpack_gimp_brush(fileresult, scan_environment, offset, unpack_dir)
'''

class GimpBrushUnpackParser(UnpackParser):
    extensions = ['.gbr']
    signatures = [
        (20, b'GIMP')
    ]
    pretty_name = 'gimpbrush'

    def calculate_unpacked_size(self):
        try:
            self.unpacked_size = self.data.header_size + self.data.body_size
        except BaseException as e:
            raise UnpackParserException(e.args)

    def parse(self):
        try:
            self.data = gimp_brush.GimpBrush.from_io(self.infile)
        # TODO: decide what exceptions to catch
        except (Exception, ValidationNotEqualError) as e:
            raise UnpackParserException(e.args)
        except BaseException as e:
            raise UnpackParserException(e.args)

        check_condition(self.data.header.version < 3, "Invalid version")
        check_condition(self.data.header.version > 0, "Invalid version")
        check_condition(self.data.header.version == 2, "Unsupported version")
        check_condition(self.data.header.width > 0, "Invalid width")
        check_condition(self.data.header.height > 0, "Invalid height")
        check_condition(self.data.header.color_depth > 0, "Invalid color depth")
        check_condition(self.data.header_size > 0, "Invalid header_size")
        unpacked_size = self.data.header_size + self.data.body_size

        check_condition(unpacked_size <= self.fileresult.filesize, "Not enough data")
        try:
            self.infile.seek(0)
            testimg = GbrImageFile(self.infile)
            testimg.load()
        except BaseException as e:
            raise UnpackParserException(e.args)

    def set_metadata_and_labels(self):
        self.unpack_results.set_labels(['gimp brush', 'graphics'])
        self.unpack_results.set_metadata({'width': self.data.width,
                                           'height': self.data.height,
                                           'color_depth': self.data.color_depth
                                        })

