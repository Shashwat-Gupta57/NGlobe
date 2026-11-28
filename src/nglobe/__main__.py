import sys
import traceback

from nglobe.main import main

try:
    main()
except Exception:
    # A double-clicked console closes instantly on a crash; leave a trace and keep it open
    from nglobe.config import HOME

    report = traceback.format_exc()
    crash_log = HOME / "logs" / "crash.log"
    try:
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        crash_log.write_text(report, encoding="utf-8")
    except OSError:
        pass
    print(report, file=sys.stderr)
    print(f"NGlobe crashed. Details saved to {crash_log}", file=sys.stderr)
    try:
        input("Press Enter to close...")
    except (EOFError, OSError):
        pass
    sys.exit(1)
