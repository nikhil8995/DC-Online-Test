"""
Leader Election Algorithm for Distributed Coding Exam Platform
Implements the Bully Algorithm for coordinator selection
"""

import threading
import time
import random
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from clock_sync import BerkeleyClock


class ElectionState(Enum):
    NORMAL = "normal"
    ELECTION = "election"
    COORDINATOR = "coordinator"


@dataclass
class ServerInfo:
    """Information about a server in the cluster"""
    server_id: str
    priority: int  # Higher number = higher priority
    status: str  # "active", "inactive"
    last_heartbeat: float
    address: str
    port: int


class BullyElection:
    """Bully Algorithm implementation for leader election"""

    def __init__(self, server_id: str, priority: int, server_count: int = 3):
        self.server_id = server_id
        self.priority = priority
        self.server_count = server_count

        # Election state
        self.state = ElectionState.NORMAL
        self.current_leader: Optional[ServerInfo] = None
        self.election_timeout = 5.0  # seconds
        self.heartbeat_interval = 2.0  # seconds

        # Server registry
        self.servers: Dict[str, ServerInfo] = {}
        self.lock = threading.Lock()

        # Clock synchronization
        # is_coordinator if only one server
        self.clock = BerkeleyClock(server_id, server_count == 1)
        self.clock.start()

        # Callbacks
        self.on_leader_change: Optional[Callable] = None
        self.on_election_start: Optional[Callable] = None

        # Threading
        self.election_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.running = False

    def register_server(self, server_info: ServerInfo) -> bool:
        """Register a server in the cluster"""
        with self.lock:
            self.servers[server_info.server_id] = server_info
            print(
                f"[{self.server_id}] Registered server {server_info.server_id} with priority {server_info.priority}")
            return True

    def unregister_server(self, server_id: str) -> bool:
        """Unregister a server from the cluster"""
        with self.lock:
            if server_id in self.servers:
                del self.servers[server_id]
                print(f"[{self.server_id}] Unregistered server {server_id}")

                # If the unregistered server was the leader, start election
                if self.current_leader and self.current_leader.server_id == server_id:
                    self.current_leader = None
                    self.start_election()
                return True
            return False

    def start_election(self) -> bool:
        """Start the bully election process"""
        with self.lock:
            if self.state == ElectionState.ELECTION:
                print(f"[{self.server_id}] Election already in progress")
                return False

            self.state = ElectionState.ELECTION
            print(f"[{self.server_id}] Starting election process...")

        # Record election start time
        election_start_time = self.clock.get_current_time()

        if self.on_election_start:
            self.on_election_start({
                "server_id": self.server_id,
                "priority": self.priority,
                "timestamp": election_start_time
            })

        # Find higher priority servers
        higher_priority_servers = self._get_higher_priority_servers()

        if not higher_priority_servers:
            # No higher priority servers, become coordinator
            self._become_coordinator()
        else:
            # Send election messages to higher priority servers
            self._send_election_messages(higher_priority_servers)

            # Start election timeout
            self._start_election_timeout()

        return True

    def _get_higher_priority_servers(self) -> List[ServerInfo]:
        """Get servers with higher priority than current server"""
        with self.lock:
            return [s for s in self.servers.values()
                    if s.priority > self.priority and s.status == "active"]

    def _send_election_messages(self, servers: List[ServerInfo]) -> None:
        """Send election messages to higher priority servers"""
        for server in servers:
            try:
                # In a real implementation, this would send RMI calls
                print(
                    f"[{self.server_id}] Sending election message to {server.server_id}")
                # Simulate message sending
                self._handle_election_message(
                    server.server_id, self.server_id, self.priority)
            except Exception as e:
                print(
                    f"[{self.server_id}] Failed to send election message to {server.server_id}: {e}")

    def _start_election_timeout(self) -> None:
        """Start election timeout thread"""
        if self.election_thread and self.election_thread.is_alive():
            return

        self.election_thread = threading.Thread(
            target=self._election_timeout_worker, daemon=True)
        self.election_thread.start()

    def _election_timeout_worker(self) -> None:
        """Worker thread for election timeout"""
        time.sleep(self.election_timeout)

        with self.lock:
            if self.state == ElectionState.ELECTION:
                print(
                    f"[{self.server_id}] Election timeout - no response from higher priority servers")
                self._become_coordinator()

    def _become_coordinator(self) -> None:
        """Become the coordinator/leader"""
        with self.lock:
            self.state = ElectionState.COORDINATOR
            self.current_leader = ServerInfo(
                server_id=self.server_id,
                priority=self.priority,
                status="active",
                last_heartbeat=time.time(),
                address="localhost",  # Would be actual address
                port=0  # Would be actual port
            )

        print(f"[{self.server_id}] I am now the coordinator!")

        # Record coordinator announcement time
        announcement_time = self.clock.get_current_time()

        # Announce to all servers
        self._announce_coordinator()

        if self.on_leader_change:
            self.on_leader_change(self.current_leader)

    def _announce_coordinator(self) -> None:
        """Announce coordinator status to all servers"""
        with self.lock:
            servers = [s for s in self.servers.values() if s.status ==
                       "active"]

        for server in servers:
            try:
                print(
                    f"[{self.server_id}] Announcing coordinator status to {server.server_id}")
                # In a real implementation, this would send RMI calls
                self._handle_coordinator_announcement(
                    server.server_id, self.server_id, self.priority)
            except Exception as e:
                print(
                    f"[{self.server_id}] Failed to announce coordinator to {server.server_id}: {e}")

    def handle_election_message(self, from_server_id: str, from_priority: int) -> bool:
        """Handle election message from another server"""
        print(f"[{self.server_id}] Received election message from {from_server_id} (priority: {from_priority})")

        # Log received message time
        received_time = self.clock.get_current_time()

        if from_priority < self.priority:
            # Respond with OK message
            print(f"[{self.server_id}] Responding OK to {from_server_id}")
            self._send_ok_message(from_server_id)
            return True
        else:
            # Ignore message from higher priority server
            print(
                f"[{self.server_id}] Ignoring message from higher priority server {from_server_id}")
            return False

    def _handle_election_message(self, from_server_id: str, from_priority: int) -> bool:
        """Internal handler for election messages (simulated)"""
        return self.handle_election_message(from_server_id, from_priority)

    def _send_ok_message(self, to_server_id: str) -> None:
        """Send OK message to server"""
        try:
            print(f"[{self.server_id}] Sending OK message to {to_server_id}")
            # In a real implementation, this would send RMI calls
            self._handle_ok_message(to_server_id, self.server_id)
        except Exception as e:
            print(
                f"[{self.server_id}] Failed to send OK message to {to_server_id}: {e}")

    def _handle_ok_message(self, from_server_id: str, from_priority: int) -> None:
        """Handle OK message from another server"""
        print(f"[{self.server_id}] Received OK message from {from_server_id}")

        # Log OK message received time
        received_time = self.clock.get_current_time()

        # Stop election process
        with self.lock:
            if self.state == ElectionState.ELECTION:
                self.state = ElectionState.NORMAL
                print(
                    f"[{self.server_id}] Stopping election - received OK from higher priority server")

    def handle_coordinator_announcement(self, leader_id: str, leader_priority: int) -> bool:
        """Handle coordinator announcement from another server"""
        print(
            f"[{self.server_id}] Received coordinator announcement from {leader_id}")

        # Log announcement received time
        received_time = self.clock.get_current_time()

        with self.lock:
            self.state = ElectionState.NORMAL
            self.current_leader = ServerInfo(
                server_id=leader_id,
                priority=leader_priority,
                status="active",
                last_heartbeat=time.time(),
                address="localhost",  # Would be actual address
                port=0  # Would be actual port
            )

        if self.on_leader_change:
            self.on_leader_change(self.current_leader)

        return True

    def _handle_coordinator_announcement(self, leader_id: str, leader_priority: int) -> bool:
        """Internal handler for coordinator announcements (simulated)"""
        return self.handle_coordinator_announcement(leader_id, leader_priority)

    def start_heartbeat(self) -> None:
        """Start heartbeat monitoring"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return

        self.running = True
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()

    def _heartbeat_worker(self) -> None:
        """Worker thread for heartbeat monitoring"""
        while self.running:
            time.sleep(self.heartbeat_interval)

            with self.lock:
                if self.state == ElectionState.COORDINATOR:
                    # Send heartbeat to all servers
                    self._send_heartbeat()
                else:
                    # Check if leader is still alive
                    if self.current_leader:
                        if time.time() - self.current_leader.last_heartbeat > self.election_timeout * 2:
                            print(
                                f"[{self.server_id}] Leader {self.current_leader.server_id} appears to be dead")
                            self.current_leader = None
                            self.start_election()

    def _send_heartbeat(self) -> None:
        """Send heartbeat to all servers"""
        with self.lock:
            servers = [s for s in self.servers.values() if s.status ==
                       "active"]

        for server in servers:
            try:
                print(f"[{self.server_id}] Sending heartbeat to {server.server_id}")
                # In a real implementation, this would send RMI calls
                self._handle_heartbeat(server.server_id, self.server_id)
            except Exception as e:
                print(
                    f"[{self.server_id}] Failed to send heartbeat to {server.server_id}: {e}")

    def _handle_heartbeat(self, from_server_id: str) -> None:
        """Handle heartbeat from another server"""
        with self.lock:
            if from_server_id in self.servers:
                self.servers[from_server_id].last_heartbeat = time.time()
                print(
                    f"[{self.server_id}] Received heartbeat from {from_server_id}")

    def is_leader(self) -> bool:
        """Check if this server is the current leader"""
        with self.lock:
            return (self.state == ElectionState.COORDINATOR and
                    self.current_leader and
                    self.current_leader.server_id == self.server_id)

    def get_leader(self) -> Optional[ServerInfo]:
        """Get current leader information"""
        with self.lock:
            return self.current_leader

    def get_server_list(self) -> List[ServerInfo]:
        """Get list of all servers"""
        with self.lock:
            return list(self.servers.values())

    def stop(self) -> None:
        """Stop the election system"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
        if self.election_thread:
            self.election_thread.join(timeout=1.0)

    def set_callbacks(self, on_leader_change: Callable = None, on_election_start: Callable = None) -> None:
        """Set callback functions for events"""
        self.on_leader_change = on_leader_change
        self.on_election_start = on_election_start
