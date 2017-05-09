import logging

from synth.engines.engine import Engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pause(Engine):
    # noinspection PyUnusedLocal
    def __init__(self, conf):
        logger.info("Created 'next key to continue' engine.")

        self.events = []
        self.index = 0

    def start_event_loop(self):
        logger.info("Started loop.")
        while True:
            raw_input("Press Enter to process {index} / {count}.\n".format(
                index=self.index, count=len(self.events)),
            )

            if self.index < len(self.events) and len(self.events[self.index]) > 0:
                for event in self.events[self.index]:
                    event()
            else:
                logger.info("No events registered.")

            self.index += 1

    def register_event_at(self, event, index):
        while len(self.events) <= index:
            self.events.append([])
        self.events[index].append(event)
        logger.info("Registered event at {index}".format(index=index))

    def register_event_in(self, event, delta):
        self.register_event_at(event, self.index + delta)
