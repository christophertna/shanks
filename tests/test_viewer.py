import unittest
from pathlib import Path

from graph import build_graph
from serve_graph import structured_mermaid, style_mermaid


class GraphViewerTests(unittest.TestCase):
    def test_viewer_refreshes_after_server_reconnect(self) -> None:
        content = (Path(__file__).parents[1] / "graph.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('graphEvents.addEventListener("open"', content)
        self.assertIn('lastDefinition = "";', content)

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
        self.assertIn("building --> failed_build;", content)
        self.assertIn("failed_build --> __end__;", content)
        self.assertIn("validation --> commit_item;", content)
        self.assertIn("commit_item --> item_router;", content)
        self.assertIn("validation --> debugger;", content)
        self.assertNotIn("github_node -.-> debugger;", content)
        self.assertIn("building --> critic_auditor;", content)
        self.assertIn("critic_auditor -.-> building;", content)
        self.assertIn("debugger -.-> planning;", content)
        self.assertIn("item_router -.-> planning;", content)

        self.assertNotIn("building --> __end__;", content)
        self.assertNotIn("validation -.-> planning;", content)

    def test_structured_view_labels_and_critic_loop(self) -> None:
        drawable_graph = build_graph().get_graph()
        decision_nodes = {
            node.id
            for node in drawable_graph.nodes.values()
            if (node.metadata or {}).get("kind") == "decision"
        }

        content = structured_mermaid(
            drawable_graph.draw_mermaid(),
            decision_nodes,
        )

        self.assertIn('planning["planning"]', content)
        self.assertIn('intake["Intake"]:::mainNode', content)
        self.assertIn('learning["Learn codebase"]:::mainNode', content)
        self.assertIn('building["Build"]:::mainNode', content)
        self.assertIn('item_router{"more items"}', content)
        self.assertIn('validation{"Validate"}:::yellowNode', content)
        self.assertIn('commit_item["commit item"]:::mainNode', content)
        self.assertIn('github_node["github node"]:::yellowNode', content)
        self.assertIn('critic_auditor["critic_auditor"]', content)
        main_section = content.split("  end", 1)[0]
        self.assertIn("building --> critic_auditor", main_section)
        self.assertIn("critic_auditor -.-> building", main_section)
        self.assertIn("validation --> commit_item", main_section)
        self.assertIn("commit_item --> item_router", main_section)
        self.assertIn("intake -.-> learning", main_section)
        self.assertIn("learning -.-> intake", main_section)
        self.assertNotIn("building --> building", main_section)
        self.assertIn("item_router -.-> planning", main_section)
        self.assertIn("item_router --> github_node", main_section)
        self.assertIn("github_node --> __end__", main_section)
        self.assertNotIn("critic_auditor -.-> validation", content)
        self.assertNotIn("critic_auditor -.-> item_router", content)

        detailed_content = structured_mermaid(
            drawable_graph.draw_mermaid(),
            decision_nodes,
            detailed=True,
        )
        self.assertIn("main -.-> recovery", detailed_content)
        self.assertIn("recovery -.-> main", detailed_content)
        self.assertNotIn("validation -.-> debugger", detailed_content)
        self.assertNotIn("github_node -.-> debugger", detailed_content)
        self.assertNotIn("building -.-> attempt_limit", detailed_content)


if __name__ == "__main__":
    unittest.main()
