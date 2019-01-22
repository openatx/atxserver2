#!/usr/bin/env python
# coding: utf-8

"""Multipart/form-data streamer for tornado 4.3"""
import os
import re
import tempfile
import hashlib
import shutil


class ParseError(Exception):
    """This exception is raised when the streamed data cannot be parsed as multipart/form-data."""
    pass


class SizeLimitError(Exception):
    """This exception is raised when the size of a single field exceeds the allowed limit."""
    pass


class StreamedPart(object):
    """Represents a part of the multipart/form-data."""

    def __init__(self, streamer, headers):
        self.streamer = streamer
        self.headers = headers
        self._size = 0

    def get_size(self):
        return self._size

    size = property(get_size, doc="Size of the streamed part. It will be a growing value while the part is streamed.")

    def feed(self, data):
        """Feed data into the stream.

        :param data: Binary string that has arrived from the client."""
        raise NotImplementedError

    def finalize(self):
        """Called after all data has arrived for the part."""
        pass

    def release(self):
        """Called when used resources should be freed up.

        This is called from MultiPartStreamer.release_parts."""
        pass

    def get_payload(self):
        """Load part data and return it as a binary string.

        Warning! This method will load the whole data into memory. First you should check the get_size() method
        the see if the data fits into memory.

        .. note:: In the base class, this is not implemented.
        """
        raise NotImplementedError

    def get_ct_params(self):
        """Get Content-Disposition parameters.

        :return:  If there is no content-disposition header for the part, then it returns an empty list.
            Otherwise it returns a list of values given for Content-Disposition headers.
        :rtype: list
        """
        for header in self.headers:
            if header.get("name", "").lower().strip() == "content-disposition":
                return header.get("params", [])
        return []

    def get_ct_param(self, name, def_val=None):
        """Get content-disposition parameter.

        :param name: Name of the parameter, case insensitive.
        :param def_val: Value to return when the parameter was not found.
        """
        ct_params = self.get_ct_params()
        for param_name in ct_params:
            if param_name.lower().strip() == name:
                return ct_params[name]
        return def_val

    def get_name(self):
        """Get name of the part.

        If the multipart form data was sent by a web browser, then the name of the part is the name of the input
        field in the form.

        :return: Name of the parameter (as given in the ``name`` parameter of the content-disposition header)
            When there is no ``name``parameter, returns None. Although all parts in multipart/form-data
            should have a name.
        """
        return self.get_ct_param("name", None)

    def get_filename(self):
        """Get filename of the part.

        If the multipart form data was sent by a web browser, then the name of the part is the filename of the input
        field in the form.

        :return: filename of the parameter (as given in the ``filename`` parameter of the content-disposition header)
            When there is no ``filename``parameter, returns None. All browsers will send this parameter to all
            file input fields.
        """
        return self.get_ct_param("filename", None)

    def is_file(self):
        """Return if the part is a posted file.

        Please note that a program can post huge amounts of data without giving a filename."""
        return bool(self.get_filename())


class TemporaryFileStreamedPart(StreamedPart):
    """A multi part streamer/part that feeds data into a named temporary file.

    This class has an ``f_out`` attribute that is bound to a NamedTemporaryFile.
    """
    def __init__(self, streamer, headers, tmp_dir=None):
        """Create a new streamed part that writes part data into a NamedTemporaryFile.

        :param streamer: The MultiPartStreamer that feeds this streamed part.
        :param headers: A dict of part headers
        :param tmp_dir: Directory for the NamedTemporaryFile. Will be passed to NamedTemporaryFile constructor.

        The NamedTemporaryFile is available through the ``f_out`` attribute. It is created with delete=False, argument,
        so the temporary file is not automatically deleted when closed. You can use the move() method to move the
        temporary file to a different location. If you do not call the move() method, then the file will be deleted
        when release() is called.
        """
        super(TemporaryFileStreamedPart, self).__init__(streamer, headers)
        self.is_moved = False
        self.is_finalized = False
        self.f_out = tempfile.NamedTemporaryFile(dir=tmp_dir, delete=False)
        self._m = hashlib.md5()
        self.md5sum = None

    def feed(self, data):
        """Feed data into the stream.

        :param data: Binary string that has arrived from the client.

        This version writes data into a temporary file."""
        self.f_out.write(data)
        self._m.update(data)

    def finalize(self):
        try:
            self.f_out.flush()
            self.is_finalized = True
            self.md5sum = self._m.hexdigest()
        finally:
            super(TemporaryFileStreamedPart, self).finalize()

    def move(self, file_path):
        """Move the temporary file to a new location.

        :param file_path: New file path for the file.

        This method will first close the temporary file, then move it to the new location.
        """
        if not self.is_finalized:
            raise Exception("Cannot move temporary file: stream is not finalized yet.")
        if self.is_moved:
            raise Exception("Cannot move temporary file: it has already been moved.")
        self.f_out.close()
        # print("tmpfile name: " + self.f_out.name)
        shutil.move(self.f_out.name, file_path)
        self.is_moved = True

    def release(self):
        """Release resources assigned to the part.

        If the temporary file has been moved with the move() method, then this method does nothing. Otherwise
        it closes the temporary file and deletes it from disk."""
        try:
            if not self.is_moved:
                self.f_out.close()
                os.unlink(self.f_out.name)
        finally:
            super(TemporaryFileStreamedPart, self).release()

    def get_payload(self):
        """Load part data from disk and return it.

        Warning! This will load the entire payload into memory!"""
        if not self.is_finalized:
            raise Exception("Cannot read temporary file: stream is not finalized yet.")
        if self.is_moved:
            raise Exception("Cannot read temporary file: it has already been moved.")
        self.f_out.seek(0)
        return self.f_out.read()


class MultiPartStreamer(object):
    """Parse a stream of multpart/form-data.

    Useful for request handlers decorated with ``tornado.web.stream_request_body``.
    """
    SEP = b"\r\n"  # line separator in multipart/form-data
    L_SEP = len(SEP)
    PAT_HEADER_VALUE = re.compile(r"""([^:]+):\s+([^\s;]+)(.*)""")
    PAT_HEADER_PARAMS = re.compile(r""";\s*([^=]+)=\"(.*?)\"(.*)""")

    # Encoding for the header values. Only header name and parameters
    # will be decoded. Streamed data will remain binary.
    # This is required because multipart/form-data headers cannot
    # be parsed without a valid encoding.
    header_encoding = "UTF-8"

    def __init__(self, total):
        """Create a new PostDataStreamer

        :param total: Total number of bytes in the stream. This is what the http client sends as
            the Content-Length header of the whole form.
        """
        self.buf = b""
        self.dlen = None
        self.delimiter = None
        self.in_data = False
        self.headers = []
        self.parts = []
        self.total = total
        self.received = 0

    def _get_raw_header(self, data):
        """Return raw header data.

        Internal method. Do not call directly.

        :param data: A string containing raw data from the form part
        :return: A tuple of (header_value, tail) where header_value is the first line of the form part.
            If there is no first line yet (e.g. the whole data is a single line) then header_value will be None.
        """
        idx = data.find(self.SEP)
        if idx >= 0:
            return data[:idx], data[idx + self.L_SEP:]
        else:
            return None, data

    def _parse_header(self, header):
        """Parse raw header data.

        Internal method. Do not call directly.

        :param header: Raw data of the part.
        :return: A dict that contains the ``name``, ``value`` and ``params`` for the header.
            If the header is a simple value, then it may only return a dict with a ``value``.
        """
        header = header.decode(self.header_encoding)
        res = self.PAT_HEADER_VALUE.match(header)
        if res:
            name, value, tail = res.groups()
            params = {}
            hdr = {"name": name, "value": value, "params": params}
            while True:
                res = self.PAT_HEADER_PARAMS.match(tail)
                if not res:
                    break
                hdr_name, hdr_value, tail = res.groups()
                params[hdr_name] = hdr_value
            return hdr
        else:
            return {"value": header}

    def _begin_part(self, headers):
        """Internal method called when a new part is started in the stream.

        :param headers: A dict of headers as returned by parse_header."""
        self.part = self.create_part(headers)
        assert isinstance(self.part, StreamedPart)
        self.parts.append(self.part)

    def _feed_part(self, data):
        """Internal method called when content is added to the current part.

        :param data: Raw data for the current part."""
        # noinspection PyProtectedMember
        self.part._size += len(data)
        self.part.feed(data)

    def _end_part(self):
        """Internal method called when receiving the current part has finished.

        The implementation of this does nothing, but it can be overriden to do something with ``self.fout``."""
        self.part.finalize()

    def data_received(self, chunk):
        """Receive a chunk of data for the form.

        :param chunk: Binary string that was received from the http(s) client.

        This method incrementally parses stream data, finds part headers and feeds binary data into created
        StreamedPart instances. You need to call this when a chunk of data is available for the part.

        This method may raise a ParseError if the received data is malformed.
        """
        self.received += len(chunk)
        self.on_progress(self.received, self.total)
        self.buf += chunk

        if not self.delimiter:
            self.delimiter, self.buf = self._get_raw_header(self.buf)
            if self.delimiter:
                self.delimiter += self.SEP
                self.dlen = len(self.delimiter)
            elif len(self.buf) > 1000:
                raise ParseError("Cannot find multipart delimiter")
            else:
                return

        while True:
            if self.in_data:
                if len(self.buf) > 3 * self.dlen:
                    idx = self.buf.find(self.SEP + self.delimiter)
                    if idx >= 0:
                        self._feed_part(self.buf[:idx])
                        self._end_part()
                        self.buf = self.buf[idx + len(self.SEP + self.delimiter):]
                        self.in_data = False
                    else:
                        limit = len(self.buf) - 2 * self.dlen
                        self._feed_part(self.buf[:limit])
                        self.buf = self.buf[limit:]
                        return
                else:
                    return
            if not self.in_data:
                while True:
                    header, self.buf = self._get_raw_header(self.buf)
                    if header == b"":
                        assert self.delimiter
                        self.in_data = True
                        self._begin_part(self.headers)
                        self.headers = []
                        break
                    elif header:
                        self.headers.append(self._parse_header(header))
                    else:
                        # Header is None, not enough data yet
                        return

    def data_complete(self):
        """Call this after the last receive() call, e.g. when all data arrived for the form.

        You MUST call this before using the parts."""
        if self.in_data:
            idx = self.buf.rfind(self.SEP + self.delimiter[:-2])
            if idx > 0:
                self._feed_part(self.buf[:idx])
            self._end_part()

    def create_part(self, headers):
        """Called when a new part needs to be created.

        :param headers: A dict of header values for the new part to be created.

        You can override this to create a custom StreamedPart. The default method creates a
        TemporaryFileStreamedPart that streams data into a named temporary file.
        """
        return TemporaryFileStreamedPart(self, headers)

    def release_parts(self):
        """Call this to release resources for all parts created.

         This method will call the release() method on all parts created for the stream."""
        [part.release() for part in self.parts]

    def get_parts_by_name(self, part_name):
        """Get a parts by name.

        :param part_name: Name of the part. This is case sensitive!

        Attention! A form may have posted multiple values for the same name. So the return value of this method is a
        list of parts!
        """
        return [part for part in self.parts if (part.get_name() == part_name)]

    def get_values(self, names, size_limit=10 * 1024):
        """Return a dictionary of values for the given field names.

        :param names: A list of field names, case sensitive.
        :param size_limit: Maximum size of the value of a single field.
            If a field's size exceeds this value, then SizeLimitError is raised.

        Caveats:

            * do not use this for big file values, because values are loaded into memory
            * a form may have posted multiple values for a field name. This method returns the first available
              value for that name. If the form might contain multiple values for the same name, then do not
              use this method.  To get all values for a name, use the get_parts_by_name method instead.

        Tip: use get_nonfile_parts() to get a list of parts that are not originally files (read the docstring)
        """
        res = {}
        for name in names:
            parts = self.get_parts_by_name(name)
            if not parts:
                raise KeyError("No such field: %s" % name)
            size = parts[0].size
            if size > size_limit:
                raise SizeLimitError("Part size=%s > limit=%s" % (size, size_limit))
            res[name] = parts[0].get_payload()
        return res

    def get_nonfile_parts(self):
        """Get a list of parts that are originally not files.

        It examines the filename attribute of the Content-Disposition header.  Be aware that these fields still may be
        huge in size. A custom http client can post huge amounts of data without giving Content-Disposition.
        """
        return [part for part in self.parts if not part.is_file()]

    def on_progress(self, received, total):
        """Override this function to handle progress of receiving data.

        :param received: Number of bytes received
        :param total: Total bytes to be received.
        """
        pass
