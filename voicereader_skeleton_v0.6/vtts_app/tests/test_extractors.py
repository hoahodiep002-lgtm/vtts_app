import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reader.extractors import extract_text


class ExtractorTests(unittest.TestCase):
    def test_txt_utf8_vietnamese(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as f:
            f.write("Xin chào Việt Nam".encode("utf-8"))
        self.assertEqual(extract_text(f.name), "Xin chào Việt Nam")
        os.unlink(f.name)

    def test_unsupported_extension(self):
        with self.assertRaises(ValueError):
            extract_text("a.xyz")

    def test_image_without_backend_is_explicit(self):
        with self.assertRaises(NotImplementedError):
            extract_text("a.png")


if __name__ == "__main__":
    unittest.main()
