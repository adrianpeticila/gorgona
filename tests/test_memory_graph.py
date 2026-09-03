import unittest
from gorgona.guards.memory_graph import MemoryGraphGuard
from tools.memory_graph_check import extract_type

class TestMemoryGraphGuard(unittest.TestCase):
    def setUp(self):
        self.guard = MemoryGraphGuard(max_depth=5, repetition_threshold=3)

    def test_cycle_detection_self_loop(self):
        self.guard.add_edge("A", "A")
        has_cycle, cycle = self.guard.detect_graph_cycle()
        self.assertTrue(has_cycle)
        self.assertEqual(cycle, ["A", "A"])

    def test_cycle_detection_tri_node(self):
        self.guard.add_edge("A", "B")
        self.guard.add_edge("B", "C")
        self.guard.add_edge("C", "A")
        has_cycle, cycle = self.guard.detect_graph_cycle()
        self.assertTrue(has_cycle)
        # the cycle path might be A->B->C->A, or start at B or C.
        self.assertEqual(len(cycle), 4)
        self.assertEqual(cycle[0], cycle[-1])

    def test_cycle_detection_dag(self):
        self.guard.add_edge("A", "B")
        self.guard.add_edge("A", "C")
        self.guard.add_edge("B", "D")
        self.guard.add_edge("C", "D")
        has_cycle, cycle = self.guard.detect_graph_cycle()
        self.assertFalse(has_cycle)

    def test_step_repetition_threshold(self):
        self.guard.record_step("Step1")
        self.guard.record_step("Step2")
        self.guard.record_step("Step1")

        # 3rd time should trigger
        report = self.guard.record_step("Step1")
        self.assertTrue(report.loop_detected)
        self.assertEqual(report.cycle_path, ["Step1", "Step1", "Step1"])
        self.assertIn("Repetitive execution detected", report.warning)

    def test_depth_limit_tracking(self):
        for i in range(5):
            report = self.guard.record_step(f"Step{i}")
            self.assertFalse(report.loop_detected)

        report = self.guard.record_step("Step6")
        self.assertTrue(report.loop_detected)
        self.assertIn("exceeded max_depth", report.warning)

    def test_frontmatter_regex(self):
        # verifies both "type: user" at column 0 and indented "  type: project" work.
        fm1 = "name: test\ntype: user\ndescription: foo"
        self.assertEqual(extract_type(fm1), "user")

        fm2 = "name: test\n  type: project\ndescription: foo"
        self.assertEqual(extract_type(fm2), "project")

if __name__ == '__main__':
    unittest.main()
