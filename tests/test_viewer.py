import unittest

from graph import build_graph
from serve_graph import style_mermaid


class GraphViewerTests(unittest.TestCase):
    def test_viewer_keeps_forward_edges_solid_and_backward_edges_dashed(self) -> None:
        drawable_graph = build_graph().get_graph()
        decision_nodes = {
            node.id
            for node in drawable_graph.nodes.values()
            if (node.metadata or {}).get("kind") == "decision"
        }

        content = style_mermaid(drawable_graph.draw_mermaid(), decision_nodes)

        self.assertIn("graph LR;", content)
        self.assertIn("validation{validation}", content)
        self.assertIn("planning --> building;", content)
        self.assertIn("building --> validation;", content)
        self.assertIn("validation --> debugger;", content)
        self.assertIn("critic_auditor --> building;", content)
        self.assertIn("building -.-> critic_auditor;", content)
        self.assertIn("debugger -.-> planning;", content)
        self.assertIn("item_router -.-> planning;", content)

        self.assertNotIn("building --> __end__;", content)
        self.assertNotIn("validation -.-> planning;", content)


if __name__ == "__main__":
    unittest.main()
