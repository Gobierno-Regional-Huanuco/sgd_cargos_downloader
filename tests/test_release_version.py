import re
import unittest

from cargos_downloader import __version__


class ReleaseVersionTest(unittest.TestCase):
    def test_application_version_is_semver(self) -> None:
        self.assertRegex(
            __version__,
            re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$"),
        )


if __name__ == "__main__":
    unittest.main()
