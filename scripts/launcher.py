import os
import sys


install_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, install_root)

try:
    from memingo.__main__ import main
except Exception as error:
    print(f"Memingo error: installation is incomplete: {error}", file=sys.stderr)
    print("Reinstall Memingo or run 'memingo update-self'.", file=sys.stderr)
    raise SystemExit(1)

raise SystemExit(main())
