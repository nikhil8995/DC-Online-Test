"""
Multi-Server Manager for Exam Platform
Runs multiple exam server instances in separate threads
"""

import threading
import time
from typing import Dict, List, Optional
from exam_server import ExamServerInstance, BerkeleyClock


class MultiServerManager:
    def __init__(self, ports=None, server_ids=None):
        self.ports = ports or [6001, 6002, 6003]
        self.server_ids = server_ids or ["S1", "S2", "S3"]
        self.instances: Dict[str, ExamServerInstance] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.running = False

    def start_servers(self):
        """Start all exam server instances"""
        self.running = True

        for port, server_id in zip(self.ports, self.server_ids):
            try:
                # Create and initialize server instance
                instance = ExamServerInstance(port, server_id)

                # First server (port 6001) is the time coordinator
                is_coordinator = (port == self.ports[0])
                instance.clock_sync = BerkeleyClock(server_id, is_coordinator)
                instance.clock_sync.start()

                # Start server in its own thread
                thread = threading.Thread(
                    target=self._run_server,
                    args=(instance,),
                    daemon=True
                )
                thread.start()

                self.instances[server_id] = instance
                self.threads[server_id] = thread

                print(f"Started exam server {server_id} on port {port}")

                # Brief pause between server starts
                time.sleep(1)

            except Exception as e:
                print(
                    f"Failed to start server {server_id} on port {port}: {e}")

        if self.instances:
            print(f"\nAll servers started successfully:")
            for server_id, instance in self.instances.items():
                print(f"- {server_id} running on port {instance.port}")
        else:
            print("Failed to start any servers!")

    def stop_servers(self):
        """Stop all running servers"""
        self.running = False

        for server_id, instance in self.instances.items():
            try:
                if instance.clock_sync:
                    instance.clock_sync.stop()
                print(f"Stopped server {server_id}")
            except Exception as e:
                print(f"Error stopping server {server_id}: {e}")

        # Wait for all threads to finish
        for thread in self.threads.values():
            thread.join(timeout=5.0)

        print("All servers stopped")

    def _run_server(self, instance: ExamServerInstance):
        """Run a single server instance"""
        try:
            instance.app.run(
                host='0.0.0.0',
                port=instance.port,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            print(f"Server {instance.server_id} crashed: {e}")


if __name__ == '__main__':
    manager = MultiServerManager()

    try:
        print("Starting exam servers...")
        manager.start_servers()

        # Keep the main thread alive
        while manager.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down servers...")
        manager.stop_servers()
