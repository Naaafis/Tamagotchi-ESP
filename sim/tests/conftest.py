"""Make `import pet` work: firmware/ is the CIRCUITPY root on the board.

Appended, not prepended: firmware/code.py must not shadow the stdlib `code`
module that pdb (and so pytest) imports.
"""

import os
import sys

FIRMWARE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "firmware")
if FIRMWARE not in sys.path:
    sys.path.append(FIRMWARE)
