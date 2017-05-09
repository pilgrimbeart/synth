import logging
import pendulum

from synth.common.conftime import get_interval, get_time
from synth.engines.engine import Engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Step(Engine):
    def __init__(self, conf):
        self.now = get_time(conf, 'start', pendulum.now()).start_of('second')
        self.start_index = self.now.int_timestamp
        runtime = get_interval(conf, 'runtime', pendulum.interval(days=1))
        self.end = (self.now + runtime).start_of('second')
        logger.info("Created stepper engine from {start} to {end}.".format(start=self.now, end=self.end))

        self.events = []

    def __time_as_index(self, time):
        return time.int_timestamp - self.start_index

    def start_event_loop(self):
        logger.info("Started loop.")
        while self.now <= self.end:
            index = self.__time_as_index(self.now)
            if index >= 1 and index < len(self.events):
                while len(self.events[index]) > 0:
                    self.events[index].pop(0)()

            self.now += pendulum.interval(seconds=1)

    def register_event_at(self, event, time):
        index = self.__time_as_index(time.end_of('second'))
        if index >= 0:
            if len(self.events) <= index:
                self.events.extend([[]] * (1 + index - len(self.events)))
            self.events[index].append(event)
            logger.info("Registered event at {time}".format(time=time))
        else:
            logger.warn("Dropped event registered in the past.")

    def register_event_in(self, event, interval):
        self.register_event_at(event, self.now + interval)
