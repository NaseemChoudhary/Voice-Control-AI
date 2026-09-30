"""JARVIS application entry point."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="JARVIS desktop assistant")
    parser.add_argument("--cli", action="store_true", help="run the terminal interface")
    args = parser.parse_args()

    if args.cli:
        from assistant.cli import run_cli
        run_cli()
    else:
        from ui.dashboard import run_dashboard
        run_dashboard()


if __name__ == "__main__":
    main()
