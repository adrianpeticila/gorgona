import unittest
from pathlib import Path
from gorgona.guards.isolation import IsolationGuard

class TestIsolationGuard(unittest.TestCase):
    def setUp(self):
        self.guard = IsolationGuard()
        self.guard.add_rule("BrandAlpha", "BrandBeta", "BetaSecret")
        self.guard.add_rule("BrandAlpha", "BrandBeta", "BrandB")

    def test_brand_rules_detection(self):
        text = "This is a clean text without secrets."
        violations = self.guard.check_content("BrandAlpha", text)
        self.assertEqual(len(violations), 0)

        text_violation = "Oops, we mentioned BetaSecret here."
        violations = self.guard.check_content("BrandAlpha", text_violation)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].foreign_brand, "BrandBeta")
        self.assertEqual(violations[0].forbidden_keyword, "BetaSecret")

    def test_word_boundary(self):
        # BrandB should match "BrandB" but NOT "BrandBExtra"
        text = "This has BrandBExtra inside."
        violations = self.guard.check_content("BrandAlpha", text)
        self.assertEqual(len(violations), 0)

        text2 = "This has BrandB."
        violations = self.guard.check_content("BrandAlpha", text2)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].forbidden_keyword, "BrandB")

    def test_case_insensitivity(self):
        text = "We have betasecret in lowercase."
        violations = self.guard.check_content("BrandAlpha", text)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].forbidden_keyword, "BetaSecret")

    def test_direct_forbidden_terms(self):
        self.guard.add_rule("BrandAlpha", "Global", "ForbiddenTerm")
        text = "This is a ForbiddenTerm test."
        violations = self.guard.check_content("BrandAlpha", text)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].forbidden_keyword, "ForbiddenTerm")

    def test_non_word_boundary_brand(self):
        self.guard.add_rule("TechCompany", "Competitor", "C++")
        text = "Folosim C++ in backend."
        violations = self.guard.check_content("TechCompany", text)
        self.assertGreater(len(violations), 0)

    def test_flexible_api_shapes(self):
        # Flat list shape
        iso1 = IsolationGuard(brand_rules={"BrandAlpha": ["SecretOne"]})
        v1 = iso1.check_content("BrandAlpha", "Leaking SecretOne here")
        self.assertTrue(len(v1) > 0)

        # Nested dict shape
        iso2 = IsolationGuard(brand_rules={"BrandAlpha": {"BrandBeta": ["SecretTwo"]}})
        # Swapped args (text, target_brand="BrandAlpha")
        v2 = iso2.check_content("Leaking SecretTwo here", target_brand="BrandAlpha")
        self.assertTrue(len(v2) > 0)


    def test_swapped_args_brand_correct(self):
        g = IsolationGuard({"BrandA": {"Foreign": ["BrandB"]}})
        violations = g.check_content("BrandB here", target_brand="BrandA")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].brand, "BrandA")
        self.assertEqual(violations[0].target_brand, "BrandA")


if __name__ == '__main__':
    unittest.main()
