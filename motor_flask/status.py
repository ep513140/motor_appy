import random
import threading
import time

from ophyd.status import MoveStatus, wait as status_wait
from ophyd.sim import SynAxis


class StatusAxis(SynAxis):
    """Axis simulation for MoveStatus creation"""
    FAILURE_RATE = 2
    MOTOR_SPEED = 1

    def set(self, position, timeout=None, wait=False):
        # Create a generic MoveStatus
        status = MoveStatus(self, position)
        # Determine whether this move was a failure
        is_failure = random.randint(1, 100) < self.FAILURE_RATE
        if is_failure:
            # If the move failed, let us pretend the motor got stuck part way
            # through the requested motion. Pick any random point between our
            # destination and our starting position
            position = random.uniform(self.position, position)
        # Begin simulating the motion by starting a background thread that will
        # mark our move as complete
        self._thread = threading.Thread(target=simulate_travel,
                                        args=(status, position, is_failure))
        self._thread.start()
        if wait:
            status_wait(status, timeout=timeout)
        return status


def simulate_travel(status, end_position, is_failure):
    """Simulate the motor in a background thread"""
    axis = status.device
    # Wait for our motor to move
    if axis.MOTOR_SPEED:
        travel_time = abs(axis.position - status.target) / axis.MOTOR_SPEED
        time.sleep(travel_time)
    axis.sim_state['readback'] = end_position
    # Mark the status as complete with the right failure flag
    status._finished(success=not is_failure)
