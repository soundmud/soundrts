#!/usr/bin/env python3
try:
    from soundrts import clientmain
except ModuleNotFoundError as exc:
    missing = exc.name or "unknown package"
    print(
        "Missing dependency:",
        missing,
        "\nInstall requirements with:\n"
        "python3 -m pip install -r requirements.txt",
    )
    raise SystemExit(1)

clientmain.main()
