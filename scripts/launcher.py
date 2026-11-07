import os
import sys


install_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, install_root)

from memingo.__main__ import main

raise SystemExit(main())
