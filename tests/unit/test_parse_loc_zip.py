"""
Tests for the parse_loc_zip function from examples/Sync/get_location_bundle_adv.py.

Validates zip→JSON parsing, comment skipping, delimiter handling,
directory skipping, encoding support, and output file creation.
"""

import base64
import contextlib
import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase, main


def _make_zip(*entries: tuple[str, str], as_base64: bool = False):
    """Build an in-memory zip containing the given (filename, content) pairs.

    Args:
        *entries: (filename, text_content) tuples to add to the zip.
        as_base64: If True, return a base64-encoded string (mimicking the
            Comlink API response format). Otherwise return a ZipFile object.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            zf.writestr(name, content)
    buf.seek(0)
    if as_base64:
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


def _import_parse_loc_zip():
    """Import parse_loc_zip without triggering the module-level side effects.

    The example script creates a SwgohComlink instance and directories at
    import time.  We patch those away so the test can import the function
    in isolation.
    """
    import importlib
    from unittest import mock

    # Patch SwgohComlink so no real HTTP client is created, and
    # Path.mkdir so no directories are created on disk.
    with (
        mock.patch("swgoh_comlink.SwgohComlink"),
        mock.patch("pathlib.Path.mkdir"),
    ):
        import sys

        # Provide the missing _VERSIONS_FILE so the module can load
        # even though the original script forgot to define it.
        spec = importlib.util.spec_from_file_location(
            "get_location_bundle_adv",
            Path(__file__).resolve().parents[2] / "examples" / "Sync" / "get_location_bundle_adv.py",
        )
        mod = importlib.util.module_from_spec(spec)
        # Inject _VERSIONS_FILE before exec so the NameError is avoided
        # at import time (it is only used inside __main__ guard anyway).
        sys.modules[spec.name] = mod
        with contextlib.suppress(NameError):
            spec.loader.exec_module(mod)
        return mod.parse_loc_zip


# Import once for the whole module
parse_loc_zip = _import_parse_loc_zip()


class TestParseLoczipBasic(TestCase):
    """Core parse_loc_zip behaviour."""

    def test_single_file_creates_json(
        self,
    ):
        """A single-entry zip produces one .json file with correct content."""
        zf = _make_zip(("Loc_ENG_US.txt", "UNIT_NAME|Darth Vader\nUNIT_DESC|Sith Lord\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)

            result_path = out / "Loc_ENG_US.json"
            self.assertTrue(result_path.exists(), f"{result_path} was not created")

            data = json.loads(result_path.read_text("utf-8"))
            self.assertEqual(data["UNIT_NAME"], "Darth Vader")
            self.assertEqual(data["UNIT_DESC"], "Sith Lord")

    def test_comment_lines_are_skipped(self):
        """Lines starting with '#' must not appear in the output."""
        zf = _make_zip(("Loc_Key_Mapping.txt", "# header comment\nKEY|value\n# trailing\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "Loc_Key_Mapping.json").read_text("utf-8"))
            self.assertEqual(data, {"KEY": "value"})

    def test_lines_without_delimiter_are_skipped(self):
        """Lines that do not contain the delimiter produce no key."""
        zf = _make_zip(("test.txt", "GOOD|yes\nBAD_LINE\nALSO_GOOD|yep\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertNotIn("BAD_LINE", data)
            self.assertEqual(len(data), 2)

    def test_multiple_delimiters_in_value(self):
        """Only the first delimiter is used for splitting (partition behaviour)."""
        zf = _make_zip(("test.txt", "KEY|value|with|pipes\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["KEY"], "value|with|pipes")

    def test_empty_value_after_delimiter(self):
        """A key with an empty value should still be stored."""
        zf = _make_zip(("test.txt", "EMPTY_VAL|\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["EMPTY_VAL"], "")


class TestParseLoczipMultiFile(TestCase):
    """Tests involving multiple zip entries."""

    def test_multiple_entries_produce_multiple_json_files(self):
        """Each text file in the zip gets its own .json output."""
        zf = _make_zip(
            ("Loc_ENG_US.txt", "A|1\n"),
            ("Loc_FRE_FR.txt", "B|2\n"),
            ("Loc_Key_Mapping.txt", "C|3\n"),
        )

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            created = sorted(p.name for p in out.iterdir())
            self.assertEqual(
                created,
                ["Loc_ENG_US.json", "Loc_FRE_FR.json", "Loc_Key_Mapping.json"],
            )

    def test_directory_entries_in_zip_are_skipped(self):
        """ZipInfo entries that are directories must not produce output files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf_write:
            # Add a directory entry (use writestr with trailing slash for <3.12 compat)
            zf_write.writestr(zipfile.ZipInfo("subdir/"), "")
            zf_write.writestr("subdir/file.txt", "K|V\n")

        zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            created = [p.name for p in out.iterdir()]
            self.assertIn("file.json", created)
            self.assertNotIn("subdir", created)


class TestParseLoczipOptions(TestCase):
    """Tests for optional parameters: delimiter, encoding."""

    def test_custom_delimiter(self):
        """A non-default delimiter should be used for splitting."""
        zf = _make_zip(("test.txt", "KEY=VALUE\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out, delimiter="=")
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["KEY"], "VALUE")

    def test_custom_encoding(self):
        """Non-UTF-8 encoded content should be handled with the encoding arg."""
        content = "KEY|héllo".encode("latin-1")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf_write:
            zf_write.writestr("test.txt", content)

        zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out, encoding="latin-1")
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["KEY"], "héllo")

    def test_output_dir_created_if_missing(self):
        """parse_loc_zip should create the output directory if it doesn't exist."""
        zf = _make_zip(("test.txt", "K|V\n"))

        with _tmp_dir() as base:
            nested = base / "a" / "b" / "c"
            parse_loc_zip(zf, output_dir=nested)
            self.assertTrue(nested.exists())
            self.assertTrue((nested / "test.json").exists())


class TestBase64RoundTrip(TestCase):
    """Verify the full decode → parse pipeline matches the example script."""

    def test_base64_zip_roundtrip(self):
        """Simulate the Comlink API response format and validate the full pipeline."""
        encoded = _make_zip(
            ("Loc_Key_Mapping.txt", "UNIT_VADER|Darth Vader\nUNIT_LUKE|Luke Skywalker\n"),
            as_base64=True,
        )

        # Simulate the API response
        mock_response = {"localizationBundle": encoded}

        # Decode exactly as the example script does
        decoded_bytes = base64.b64decode(mock_response["localizationBundle"])
        zf = zipfile.ZipFile(io.BytesIO(decoded_bytes))

        self.assertEqual(zf.namelist(), ["Loc_Key_Mapping.txt"])

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "Loc_Key_Mapping.json").read_text("utf-8"))
            self.assertEqual(data["UNIT_VADER"], "Darth Vader")
            self.assertEqual(data["UNIT_LUKE"], "Luke Skywalker")


class TestEdgeCases(TestCase):
    """Edge cases and boundary conditions."""

    def test_empty_zip(self):
        """An empty zip should produce no output files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass
        zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            self.assertEqual(list(out.iterdir()), [])

    def test_empty_file_in_zip(self):
        """A zip entry with no content should produce a JSON file with an empty dict."""
        zf = _make_zip(("empty.txt", ""))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "empty.json").read_text("utf-8"))
            self.assertEqual(data, {})

    def test_crlf_line_endings(self):
        """Windows-style line endings should be handled correctly."""
        zf = _make_zip(("test.txt", "K1|V1\r\nK2|V2\r\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["K1"], "V1")
            self.assertEqual(data["K2"], "V2")

    def test_unicode_content(self):
        """Non-ASCII UTF-8 content should be preserved."""
        zf = _make_zip(("test.txt", "GREETING|こんにちは\nNAME|Ñoño\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            data = json.loads((out / "test.json").read_text("utf-8"))
            self.assertEqual(data["GREETING"], "こんにちは")
            self.assertEqual(data["NAME"], "Ñoño")

    def test_json_output_uses_ensure_ascii_false(self):
        """Output JSON should not escape non-ASCII characters."""
        zf = _make_zip(("test.txt", "KEY|café\n"))

        with _tmp_dir() as out:
            parse_loc_zip(zf, output_dir=out)
            raw = (out / "test.json").read_text("utf-8")
            self.assertIn("café", raw)
            self.assertNotIn("\\u", raw)


# ── helpers ──────────────────────────────────────────────────────────


@contextlib.contextmanager
def _tmp_dir():
    """Yield a temporary directory Path that is cleaned up afterwards."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


if __name__ == "__main__":
    main()
