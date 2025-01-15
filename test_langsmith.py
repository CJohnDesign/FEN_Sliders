"""Test LangSmith integration."""
from agents.config.langsmith import get_tracing_context, client

def main():
    """Run a simple test of LangSmith tracing."""
    print("Current projects:", [p.name for p in client.list_projects()])
    
    with get_tracing_context("test-trace"):
        print("Tracing enabled for test-trace project")

if __name__ == "__main__":
    main() 