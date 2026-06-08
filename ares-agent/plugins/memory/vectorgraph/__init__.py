import os
import json
import logging
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)

# Tool schemas
STORE_SCHEMA = {
    "name": "vectorgraph_store",
    "description": (
        "Manage concepts and relationships in the Vector Graph Knowledgebase. "
        "Allows adding new facts, searching concepts semantically, connecting concepts, or removing them."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "connect", "search", "remove"],
                "description": "The action to perform: 'add' (insert fact), 'connect' (create relationship), 'search' (find similarities), 'remove' (delete fact)."
            },
            "content": {
                "type": "string",
                "description": "The fact/concept content to add, or the source fact content/ID to connect."
            },
            "category": {
                "type": "string",
                "enum": ["general", "preference", "project_context", "tech_stack", "personal"],
                "description": "Category for the concept. Defaults to 'general' (auto-categorized if omitted)."
            },
            "target": {
                "type": "string",
                "description": "The target fact content or target fact ID for establishing a relationship (required for action='connect')."
            },
            "relationship": {
                "type": "string",
                "description": "The description/type of connection (e.g., 'depends_on', 'implements', 'part_of', 'related_to'). Required for action='connect'."
            },
            "query": {
                "type": "string",
                "description": "The query for semantic search (required for action='search')."
            },
            "fact_id": {
                "type": "integer",
                "description": "The ID of the fact to remove (required for action='remove' if content is not specified)."
            }
        },
        "required": ["action"]
    }
}

VISUALIZE_SCHEMA = {
    "name": "vectorgraph_visualize",
    "description": "Export the concept network and retrieve the local URL to view the interactive vector graph visualizer.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

class VectorGraphMemoryProvider(MemoryProvider):
    """Vector Graph Memory Provider with TF-IDF similarity and explicit model connections."""

    def __init__(self):
        self.store = None
        self.db_path = ""
        self.js_path = ""
        self.html_path = ""
        self.ares_home = ""

    @property
    def name(self) -> str:
        return "vectorgraph"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        from ares_constants import get_ares_home
        self.ares_home = kwargs.get("ares_home") or os.environ.get("ARES_HOME") or str(get_ares_home())
        
        self.db_path = os.path.join(self.ares_home, "vectorgraph.db")
        self.js_path = os.path.join(self.ares_home, "graph_data.js")
        self.html_path = os.path.join(self.ares_home, "visual_memory.html")

        from plugins.memory.vectorgraph.store import VectorGraphStore
        self.store = VectorGraphStore(self.db_path)
        
        # Ensure we write initial graph_data.js
        self.store.export_graph_js(self.js_path)
        
        # Ensure visual_memory.html is created
        self._ensure_html_file()

    def system_prompt_block(self) -> str:
        return (
            "# Vector Graph Knowledgebase\n"
            "Active. Facts and relationships are stored locally in a vector database.\n"
            "Use the `vectorgraph_store` tool to add/connect/search concepts.\n"
            "Use the `vectorgraph_visualize` tool to export and get the link to view the graph.\n"
            "Keep the knowledgebase updated with key facts, user preferences, and project relationships.\n"
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self.store or not query.strip():
            return ""
        
        try:
            results = self.store.search_facts(query, limit=5)
            if not results:
                return ""
            
            lines = []
            for r in results:
                score = r["score"]
                fact = r["fact"]
                lines.append(f"- [Similarity: {score:.2f}] [ID: {fact['id']}] ({fact['category']}) {fact['content']}")
            
            return "## Vector Graph Memory Recall (Semantically Related Facts):\n" + "\n".join(lines)
        except Exception as e:
            logger.debug(f"VectorGraph prefetch failed: {e}")
            return ""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [STORE_SCHEMA, VISUALIZE_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if not self.store:
            return tool_error("VectorGraph provider not initialized.")

        if tool_name == "vectorgraph_store":
            action = args.get("action")
            if action == "add":
                content = args.get("content")
                if not content:
                    return tool_error("Missing required parameter 'content' for action='add'.")
                category = args.get("category", "general")
                fact_id = self.store.add_fact(content, category)
                self.store.export_graph_js(self.js_path)
                return json.dumps({
                    "result": "Fact successfully added.",
                    "fact_id": fact_id,
                    "content": content,
                    "category": category
                })

            elif action == "connect":
                content = args.get("content")
                target = args.get("target")
                relationship = args.get("relationship")
                if not content or not target or not relationship:
                    return tool_error("Missing parameters 'content', 'target', or 'relationship' for action='connect'.")
                
                # Retrieve source ID
                try:
                    s_id = int(content)
                except ValueError:
                    s_id = self.store.add_fact(content)
                
                # Retrieve target ID
                try:
                    t_id = int(target)
                except ValueError:
                    t_id = self.store.add_fact(target)
                
                if s_id == -1 or t_id == -1:
                    return tool_error("Failed to resolve source or target concept to a fact ID.")
                
                self.store.add_connection(s_id, t_id, relationship)
                self.store.export_graph_js(self.js_path)
                return json.dumps({
                    "result": "Relationship successfully established.",
                    "source_id": s_id,
                    "target_id": t_id,
                    "relationship": relationship
                })

            elif action == "search":
                query = args.get("query")
                if not query:
                    return tool_error("Missing required parameter 'query' for action='search'.")
                results = self.store.search_facts(query, limit=10)
                formatted = []
                for r in results:
                    formatted.append({
                        "score": r["score"],
                        "id": r["fact"]["id"],
                        "content": r["fact"]["content"],
                        "category": r["fact"]["category"]
                    })
                return json.dumps({
                    "results": formatted,
                    "count": len(formatted)
                })

            elif action == "remove":
                fact_id = args.get("fact_id")
                content = args.get("content")
                if fact_id is None and not content:
                    return tool_error("Must specify either 'fact_id' or 'content' for action='remove'.")
                
                if fact_id is None:
                    # Find fact ID by exact content
                    facts = self.store.get_all_facts()
                    matched = [f for f in facts if f["content"] == content.strip()]
                    if not matched:
                        return tool_error(f"No fact found matching content: {content}")
                    fact_id = matched[0]["id"]
                
                self.store.remove_fact(fact_id)
                self.store.export_graph_js(self.js_path)
                return json.dumps({
                    "result": "Fact successfully removed.",
                    "fact_id": fact_id
                })

            else:
                return tool_error(f"Unknown action: {action}")

        elif tool_name == "vectorgraph_visualize":
            try:
                self.store.export_graph_js(self.js_path)
                self._ensure_html_file()
                file_url = f"file:///{self.html_path.replace(os.sep, '/')}"
                return json.dumps({
                    "result": "Graph successfully updated.",
                    "html_path": self.html_path,
                    "js_path": self.js_path,
                    "url": file_url,
                    "instructions": f"Open the following link in your browser to view the interactive vector graph: {file_url}"
                })
            except Exception as e:
                return tool_error(f"Failed to visualize: {e}")

        return tool_error(f"Unknown tool: {tool_name}")

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.store:
            return
        
        # Mirror built-in memory writes
        if action == "add":
            category = "preference" if target == "user" else "general"
            self.store.add_fact(content, category)
            self.store.export_graph_js(self.js_path)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        if self.store:
            self.store.export_graph_js(self.js_path)

    def _ensure_html_file(self):
        # Write/Update the HTML file at html_path
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE)

def register(ctx) -> None:
    ctx.register_memory_provider(VectorGraphMemoryProvider())

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ares Vector Graph Knowledgebase</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <!-- vis-network CDN -->
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {
            --bg-color: #0b0f19;
            --sidebar-bg: #111827;
            --border-color: #1f2937;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-color: #6366f1;
            
            /* Category Colors */
            --cat-general: #9ca3af;
            --cat-preference: #10b981;
            --cat-project: #3b82f6;
            --cat-tech: #8b5cf6;
            --cat-personal: #ec4899;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar styling */
        #sidebar {
            width: 380px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 20px;
            box-sizing: border-box;
            z-index: 10;
            box-shadow: 5px 0 15px rgba(0,0,0,0.5);
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 800;
            margin-top: 0;
            margin-bottom: 5px;
            background: linear-gradient(135deg, #a5b4fc, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 25px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }

        .section-title {
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
            margin-top: 20px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Controls */
        .control-group {
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
        }

        .slider-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        input[type="range"] {
            flex-grow: 1;
            accent-color: var(--accent-color);
            background: var(--border-color);
            border-radius: 4px;
            height: 6px;
            outline: none;
        }

        .slider-val {
            font-family: monospace;
            font-size: 13px;
            min-width: 30px;
            text-align: right;
        }

        input[type="text"] {
            width: 100%;
            padding: 10px 12px;
            border-radius: 6px;
            background-color: var(--bg-color);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            font-size: 14px;
            box-sizing: border-box;
            outline: none;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus {
            border-color: var(--accent-color);
        }

        /* Details card */
        #details-card {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin-top: auto;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 50%;
            overflow-y: auto;
        }

        .card-placeholder {
            color: var(--text-muted);
            font-style: italic;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }

        .tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            width: fit-content;
        }

        .tag-preference { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .tag-project_context { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
        .tag-tech_stack { background-color: rgba(139, 92, 246, 0.15); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.3); }
        .tag-personal { background-color: rgba(236, 72, 153, 0.15); color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.3); }
        .tag-general { background-color: rgba(156, 163, 171, 0.15); color: #9ca3af; border: 1px solid rgba(156, 163, 171, 0.3); }

        .detail-title {
            font-family: 'Outfit', sans-serif;
            font-size: 15px;
            font-weight: 600;
        }

        .detail-desc {
            font-size: 13px;
            line-height: 1.4;
            color: var(--text-muted);
        }

        /* Main visualization canvas */
        #canvas-container {
            flex-grow: 1;
            position: relative;
            background: radial-gradient(circle at 50% 50%, #111827 0%, #0b0f19 100%);
        }

        #network {
            width: 100%;
            height: 100%;
        }

        /* Legend overlay */
        #legend {
            position: absolute;
            bottom: 20px;
            right: 20px;
            background-color: rgba(17, 24, 39, 0.85);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 15px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 5;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }

        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
    </style>
</head>
<body>
    <div id="sidebar">
        <h1>Ares Knowledge Graph</h1>
        <div class="subtitle">Vector Memory Visualizer</div>

        <div class="section-title">Filters & Thresholds</div>
        
        <div class="control-group">
            <label for="threshold">Similarity Edge Cutoff</label>
            <div class="slider-container">
                <input type="range" id="threshold" min="0.15" max="0.80" step="0.05" value="0.20">
                <div class="slider-val" id="threshold-val">0.20</div>
            </div>
        </div>

        <div class="control-group">
            <label for="search">Search Concepts</label>
            <input type="text" id="search" placeholder="Type to highlight nodes...">
        </div>

        <div class="section-title">Concept Details</div>
        <div id="details-card">
            <div class="card-placeholder">Click a node to view connections and details</div>
        </div>
    </div>

    <div id="canvas-container">
        <div id="network"></div>
        
        <div id="legend">
            <div class="legend-item">
                <div class="legend-dot" style="background-color: var(--cat-preference)"></div>
                <span>User Preference</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background-color: var(--cat-project)"></div>
                <span>Project Context</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background-color: var(--cat-tech)"></div>
                <span>Tech Stack</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background-color: var(--cat-personal)"></div>
                <span>Personal</span>
            </div>
            <div class="legend-item">
                <div class="legend-dot" style="background-color: var(--cat-general)"></div>
                <span>General Concept</span>
            </div>
        </div>
    </div>

    <!-- Load graph data dynamically -->
    <script src="graph_data.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const data = window.GRAPH_DATA || { nodes: [], edges: [], updated_at: "Unknown" };
            
            const thresholdInput = document.getElementById("threshold");
            const thresholdVal = document.getElementById("threshold-val");
            const searchInput = document.getElementById("search");
            const detailsCard = document.getElementById("details-card");

            let network = null;
            let nodesDataSet = new vis.DataSet();
            let edgesDataSet = new vis.DataSet();

            const colors = {
                preference: "#10b981",
                project_context: "#3b82f6",
                tech_stack: "#8b5cf6",
                personal: "#ec4899",
                general: "#9ca3af"
            };

            function drawNetwork() {
                const threshold = parseFloat(thresholdInput.value);
                const searchVal = searchInput.value.toLowerCase();

                // Clear previous
                nodesDataSet.clear();
                edgesDataSet.clear();

                // Format nodes
                const formattedNodes = data.nodes.map(n => {
                    const isMatched = searchVal ? n.label.toLowerCase().includes(searchVal) : true;
                    const baseColor = colors[n.category] || colors.general;
                    return {
                        id: n.id,
                        label: n.label.length > 30 ? n.label.substring(0, 30) + "..." : n.label,
                        title: n.label,
                        category: n.category,
                        timestamp: n.timestamp,
                        color: {
                            background: baseColor,
                            border: "#1f2937",
                            highlight: {
                                background: baseColor,
                                border: "#6366f1"
                            }
                        },
                        font: {
                            color: "#f3f4f6",
                            face: "Inter",
                            size: 13
                        },
                        shadow: {
                            enabled: true,
                            color: "rgba(0,0,0,0.5)",
                            size: 10,
                            x: 3,
                            y: 3
                        },
                        borderWidth: isMatched && searchVal ? 3 : 1,
                        opacity: isMatched ? 1.0 : 0.25,
                        shape: "box",
                        margin: 10
                    };
                });

                // Filter edges by threshold
                const formattedEdges = data.edges.filter(e => {
                    if (e.type === "similarity") {
                        return e.weight >= threshold;
                    }
                    return true;
                }).map(e => {
                    const isSimilarity = e.type === "similarity";
                    return {
                        from: e.from,
                        to: e.to,
                        value: e.weight,
                        title: isSimilarity ? `Similarity: ${(e.weight * 100).toFixed(0)}%` : `${e.type}: ${e.description || ""}`,
                        color: {
                            color: isSimilarity ? "rgba(99, 102, 241, 0.25)" : "#f59e0b",
                            highlight: isSimilarity ? "rgba(99, 102, 241, 0.8)" : "#f59e0b"
                        },
                        width: isSimilarity ? e.weight * 3 : 2,
                        dashes: isSimilarity,
                        arrows: isSimilarity ? "" : "to"
                    };
                });

                nodesDataSet.add(formattedNodes);
                edgesDataSet.add(formattedEdges);

                const container = document.getElementById("network");
                const graphData = {
                    nodes: nodesDataSet,
                    edges: edgesDataSet
                };

                const options = {
                    physics: {
                        solver: "forceAtlas2Based",
                        forceAtlas2Based: {
                            gravitationalConstant: -50,
                            centralGravity: 0.01,
                            springLength: 100,
                            springConstant: 0.08
                        },
                        stabilization: {
                            iterations: 150,
                            updateInterval: 25
                        }
                    },
                    interaction: {
                        hover: true,
                        tooltipDelay: 200
                    }
                };

                network = new vis.Network(container, graphData, options);

                network.on("selectNode", (params) => {
                    const nodeId = params.nodes[0];
                    const node = data.nodes.find(n => n.id === nodeId);
                    if (node) {
                        const date = new Date(node.timestamp * 1000).toLocaleString();
                        
                        // Find connected edges
                        const nodeEdges = data.edges.filter(e => e.from === nodeId || e.to === nodeId);
                        let relationsHtml = "";
                        if (nodeEdges.length > 0) {
                            relationsHtml = `<div style="margin-top: 10px; font-weight: 600; font-size: 12px; color: var(--text-muted);">CONNECTIONS:</div>`;
                            nodeEdges.forEach(e => {
                                const otherId = e.from === nodeId ? e.to : e.from;
                                const otherNode = data.nodes.find(n => n.id === otherId);
                                const otherLabel = otherNode ? (otherNode.label.length > 40 ? otherNode.label.substring(0, 40) + "..." : otherNode.label) : "Unknown";
                                if (e.type === "similarity") {
                                    relationsHtml += `<div style="font-size: 11px; margin-top: 4px;">🔗 Similar to "${otherLabel}" (${(e.weight * 100).toFixed(0)}%)</div>`;
                                } else {
                                    relationsHtml += `<div style="font-size: 11px; margin-top: 4px; color: #f59e0b;">⚡ ${e.type} -> "${otherLabel}" (${e.description || ""})</div>`;
                                }
                            });
                        }

                        detailsCard.innerHTML = `
                            <span class="tag tag-${node.category}">${node.category.replace('_', ' ')}</span>
                            <div class="detail-title">Concept #${node.id}</div>
                            <div class="detail-desc">"${node.label}"</div>
                            <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px;">Created: ${date}</div>
                            ${relationsHtml}
                        `;
                    }
                });

                network.on("deselectNode", () => {
                    detailsCard.innerHTML = `<div class="card-placeholder">Click a node to view connections and details</div>`;
                });
            }

            thresholdInput.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value).toFixed(2);
                thresholdVal.textContent = val;
                drawNetwork();
            });

            searchInput.addEventListener("input", () => {
                drawNetwork();
            });

            // Initial Draw
            drawNetwork();
        });
    </script>
</body>
</html>
"""
