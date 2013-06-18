SHOCK_DEBUG=True
def debugprint(text):
    if SHOCK_DEBUG:
        print("DEBUG: " + text)

from pdb import set_trace as strace
