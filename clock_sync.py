"""
Berkeley Clock Synchronization Algorithm for Distributed Exam Platform
Ensures consistent timing across exam servers and clients
"""

import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics


@dataclass
class TimeOffset:
    """Represents time offset information for a node"""
    node_id: str
    offset: float  # difference from coordinator's time
    rtt: float    # round trip time


class BerkeleyClock:
    def __init__(self, node_id: str, is_coordinator: bool = False):
        self.node_id = node_id
        self.is_coordinator = is_coordinator
        self.time_offset = 0.0  # Offset from system time
        self.last_sync = 0.0    # Last sync timestamp
        self.sync_interval = 5.0  # Sync every 5 seconds
        self.client_offsets: Dict[str, TimeOffset] = {}
        self.lock = threading.Lock()
        self.running = False
        self.sync_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the clock synchronization process"""
        self.running = True
        if self.is_coordinator:
            self.sync_thread = threading.Thread(
                target=self._coordinator_sync_loop)
        else:
            self.sync_thread = threading.Thread(target=self._client_sync_loop)
        self.sync_thread.daemon = True
        self.sync_thread.start()

    def stop(self):
        """Stop the clock synchronization process"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join()

    def get_current_time(self) -> float:
        """Get the current synchronized time"""
        with self.lock:
            return time.time() + self.time_offset

    def get_time_remaining(self, end_time: float) -> float:
        """Get remaining time for exam sessions"""
        current_time = self.get_current_time()
        remaining = end_time - current_time
        return max(0, remaining)  # Don't return negative time

    def _coordinator_sync_loop(self):
        """Coordinator's sync loop - implements Berkeley Algorithm"""
        while self.running:
            with self.lock:
                # 1. Request time from all clients
                client_times = self._collect_client_times()

                if client_times:
                    # 2. Calculate average offset
                    coordinator_time = time.time()
                    offsets = []

                    # Add coordinator's offset (0)
                    offsets.append(0)

                    # Calculate offsets from coordinator
                    for client_id, client_data in client_times.items():
                        client_time = client_data['time']
                        offset = client_time - coordinator_time
                        rtt = client_data['rtt']

                        # Store client offset information
                        self.client_offsets[client_id] = TimeOffset(
                            node_id=client_id,
                            offset=offset,
                            rtt=rtt
                        )
                        offsets.append(offset)

                    # 3. Calculate average offset (Berkeley Algorithm)
                    average_offset = statistics.mean(offsets)

                    # 4. Send adjustments to clients
                    self._send_time_adjustments(average_offset)

                    # 5. Adjust coordinator's time
                    self.time_offset = average_offset

            time.sleep(self.sync_interval)

    def _client_sync_loop(self):
        """Client's sync loop - responds to coordinator's sync requests"""
        while self.running:
            with self.lock:
                if time.time() - self.last_sync >= self.sync_interval:
                    # Simulate receiving time request from coordinator
                    local_time = time.time() + self.time_offset
                    # Simulate sending time to coordinator
                    # In a real implementation, this would be network communication

                    self.last_sync = time.time()

            time.sleep(1)  # Check less frequently than coordinator

    def _collect_client_times(self) -> Dict[str, Dict]:
        """Collect time samples from all clients
        Returns: Dict[client_id, {'time': timestamp, 'rtt': round_trip_time}]
        """
        # In a real implementation, this would involve network communication
        # Here we simulate collecting times from clients
        client_times = {}

        # Simulate collecting times from connected clients
        # This would be replaced with actual RPC calls
        return client_times

    def _send_time_adjustments(self, average_offset: float):
        """Send time adjustments to all clients"""
        # In a real implementation, this would involve network communication
        # Here we simulate sending adjustments
        for client_id, offset_data in self.client_offsets.items():
            adjustment = average_offset - offset_data.offset
            # Simulate sending adjustment to client
            # This would be replaced with actual RPC calls

    def adjust_time(self, adjustment: float):
        """Apply a time adjustment received from coordinator"""
        with self.lock:
            self.time_offset += adjustment
            self.last_sync = time.time()

    def set_coordinator(self, is_coordinator: bool):
        """Update the node's coordinator status"""
        was_coordinator = self.is_coordinator
        self.is_coordinator = is_coordinator

        # Restart sync process if coordinator status changed
        if was_coordinator != is_coordinator and self.running:
            self.stop()
            self.start()
