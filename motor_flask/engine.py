
from bluesky import RunEngine
from bluesky.plans import scan
from bluesky.callbacks.best_effort import BestEffortCallback
from ophyd.sim import SynGauss

from status import StatusAxis

# Create simulated devices
motor = StatusAxis(name='motor')
det = SynGauss('det', motor, 'motor', center=0, Imax=1, sigma=1)
det.kind = 'hinted'

# Create our RunEngine
RE = RunEngine()
RE.subscribe(BestEffortCallback())
