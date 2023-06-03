from unittest import TestCase

from s3proxy import main


class TestCommandLineInterface(TestCase):
    def test_cli(self):
        with self.assertRaises(SystemExit):
            main.cli()
