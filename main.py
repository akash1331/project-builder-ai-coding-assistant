"""Command-line entry point for Project Builder – AI Coding Assistant.

Prompts the user for a project description, runs it through the multi-agent
LangGraph pipeline (planner -> architect -> coder) and prints the final state.
"""
import argparse
import sys
import traceback

from agent.graph import agent
from agent.tools import PROJECT_ROOT


def main():
    """Parse CLI arguments, collect the user's prompt, and run the agent graph."""
    parser = argparse.ArgumentParser(description="Run engineering project planner")
    parser.add_argument("--recursion-limit", "-r", type=int, default=100,
                        help="Recursion limit for processing (default: 100)")

    args = parser.parse_args()

    try:
        user_prompt = input("Enter your project prompt: ")
        result = agent.invoke(
            {"user_prompt": user_prompt},
            {"recursion_limit": args.recursion_limit}
        )
        print("Final State:", result)
        print(f"\nProject generated in: {PROJECT_ROOT}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()