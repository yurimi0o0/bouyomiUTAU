"""Launch the native GUI by default, or the optional HTTP server."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="UTAU単独音をGUIでしゃべらせます")
    parser.add_argument("--server", action="store_true", help="GUIではなくHTTPサーバーを起動します")
    args, remaining = parser.parse_known_args()
    if args.server:
        sys.argv = [sys.argv[0], *remaining]
        from .server import main as server_main

        server_main()
    elif remaining:
        parser.error(f"認識できない引数です: {' '.join(remaining)}")
    else:
        from .gui import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
