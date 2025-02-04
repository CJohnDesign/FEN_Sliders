"""
FEN Builder Agent
"""
from .state import BuilderState
from .graph import create_builder_graph

async def run_builder(state: BuilderState) -> BuilderState:
    """Run the builder workflow."""
    # Create graph with initial state
    graph = create_builder_graph(state)
    
    # Run graph
    final_state = await graph.arun(state)
    return final_state 