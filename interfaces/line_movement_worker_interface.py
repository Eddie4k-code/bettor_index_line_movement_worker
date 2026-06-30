from abc import ABC, abstractmethod


class LineMovementWorkerInterface(ABC):
    @abstractmethod
    def process_batch(self, batch_size: int = 100) -> bool:
        """
        Fetch and process a batch of unanalyzed prop history rows.

        Returns True if a batch was processed, False if the queue was empty.
        """
        pass
