# Binary Analysis Next Generation (BANG!)
#
# This file is part of BANG.
#
# BANG is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License, version 3,
# as published by the Free Software Foundation.
#
# BANG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License, version 3, along with BANG.  If not, see
# <http://www.gnu.org/licenses/>
#
# Copyright Armijn Hemel
# Licensed under the terms of the GNU Affero General Public License
# version 3
# SPDX-License-Identifier: AGPL-3.0-only


import os
import collections
import xml.dom
import defusedxml
from UnpackParser import WrappedUnpackParser
from bangunpack import unpack_xar

from UnpackParser import UnpackParser, check_condition
from UnpackParserException import UnpackParserException
from kaitaistruct import ValidationNotEqualError
from . import xar


#class XarUnpackParser(UnpackParser):
class XarUnpackParser(WrappedUnpackParser):
    extensions = []
    signatures = [
        (0, b'\x78\x61\x72\x21')
    ]
    pretty_name = 'xar'

    def unpack_function(self, fileresult, scan_environment, offset, unpack_dir):
        return unpack_xar(fileresult, scan_environment, offset, unpack_dir)

    def parse(self):
        try:
            self.data = xar.Xar.from_io(self.infile)
        except (Exception, ValidationNotEqualError) as e:
            raise UnpackParserException(e.args)
        check_condition(len(self.data._raw__raw_toc) == self.data.header.len_toc_compressed,
                        "invalid compressed TOC length")
        check_condition(len(self.data.toc.xml_string) == self.data.header.toc_length_uncompressed,
                        "invalid uncompressed TOC length")

        # parse the TOC
        try:
            tocdom = defusedxml.minidom.parseString(self.data.toc.xml_string)
        except Exception as e:
            raise UnpackParserException(e.args)

        # traverse the TOC for sanity checks
        check_condition(tocdom.documentElement.tagName == 'xar',
                        "invalid TOC, \"xar\" is not the top level element")

        # there should be one single node called "toc". If not, it
        # is a malformed XAR table of contents.
        havevalidtoc = False
        for i in tocdom.documentElement.childNodes:
            # the childnodes of the element could also
            # include text nodes, which are not interesting
            if i.nodeType == xml.dom.Node.ELEMENT_NODE:
                if i.tagName == 'toc':
                    havevalidtoc = True
                    tocnode = i
                    break

        check_condition(havevalidtoc, "invalid TOC, \"toc\" element not found")

        # Then further traverse the DOM for sanity checks
        maxoffset = -1

        # offsets are relative to the end of the header
        end_of_header = self.data._io.pos()

        # the XML consists of a top level checksum, followed by metadata
        # for each file in the archive. The metadata for file includes offset
        # and length for the file itself as well as any extra metadata like
        # resource forks or extended attributes. This extra metadata is
        # optional.
        for child_node in tocnode.childNodes:
            if child_node.nodeType == xml.dom.Node.ELEMENT_NODE:
                if child_node.tagName == 'checksum':
                    # top level checksum should have a size field and offset
                    for ic in child_node.childNodes:
                        if ic.nodeType == xml.dom.Node.ELEMENT_NODE:
                            if ic.tagName == 'offset':
                                # traverse the child nodes
                                for dd in ic.childNodes:
                                    if dd.nodeType == xml.dom.Node.TEXT_NODE:
                                        checksumoffset = dd.data.strip()
                            elif ic.tagName == 'size':
                                # traverse the child nodes
                                for dd in ic.childNodes:
                                    if dd.nodeType == xml.dom.Node.TEXT_NODE:
                                        checksumsize = dd.data.strip()
                    try:
                        checksumoffset = int(checksumoffset)
                        checksumsize = int(checksumsize)
                    except ValueError as e:
                        raise UnpackParserException(e.args)
                    check_condition(end_of_header + checksumoffset + checksumsize <= self.fileresult.filesize,
                                    "checksum cannot be outside of file")
                    maxoffset = max(maxoffset, end_of_header + checksumoffset + checksumsize)
                elif child_node.tagName == 'file':
                    for ic in child_node.childNodes:
                        if ic.nodeType == xml.dom.Node.ELEMENT_NODE:
                            if ic.tagName in ['data', 'ea']:
                                for file_node in ic.childNodes:
                                    if file_node.nodeType == xml.dom.Node.ELEMENT_NODE:
                                        if file_node.tagName == 'offset':
                                            # traverse the child nodes
                                            for dd in file_node.childNodes:
                                                if dd.nodeType == xml.dom.Node.TEXT_NODE:
                                                    try:
                                                        data_offset = int(dd.data.strip())
                                                    except ValueError as e:
                                                        raise UnpackParserException(e.args)
                                        elif file_node.tagName == 'length':
                                            # traverse the child nodes
                                            for dd in file_node.childNodes:
                                                if dd.nodeType == xml.dom.Node.TEXT_NODE:
                                                    try:
                                                        data_length = int(dd.data.strip())
                                                    except ValueError as e:
                                                        raise UnpackParserException(e.args)
                                check_condition(end_of_header + data_offset + data_length <= self.fileresult.filesize,
                                    "file data cannot be outside of file")

    #def unpack(self):
    #    """extract any files from the input file"""
    #    return []

    def set_metadata_and_labels(self):
        """sets metadata and labels for the unpackresults"""
        labels = ['archive', 'xar']

        self.unpack_results.set_metadata(metadata)
        self.unpack_results.set_labels(labels)
