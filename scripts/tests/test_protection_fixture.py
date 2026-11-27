import unittest

class ProtectionFixture(unittest.TestCase):
    def test_expected_failure(self):
        self.fail("Disposable #142 required-check rejection fixture")
