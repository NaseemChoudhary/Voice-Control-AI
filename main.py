"""JARVIS application entry point."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="JARVIS assistant")
    parser.add_argument(
        "--cli", "--no-dashboard", "--no-Dashboard",
        action="store_true",
        help="run in the terminal without creating the dashboard",
    )
    args = parser.parse_args()

    if args.cli:
        from assistant.cli import run_cli
        run_cli()
    else:
        from ui.dashboard import run_dashboard
        run_dashboard()


if __name__ == "__main__":
    main()
