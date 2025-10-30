"""
RMI Interfaces for Distributed Coding Exam Platform
Defines remote interfaces for communication between components
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ServerStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    LEADER = "leader"
    FOLLOWER = "follower"


@dataclass
class ExamQuestion:
    """Represents a coding exam question"""
    id: int
    title: str
    description: str
    difficulty: str
    time_limit: int  # seconds
    # [{"input": "...", "expected_output": "...", "is_hidden": bool}]
    test_cases: List[Dict[str, Any]]
    starter_code: str
    language: str = "python"


@dataclass
class ExamSession:
    """Represents an active exam session"""
    session_id: str
    student_id: str
    exam_id: str
    start_time: float
    end_time: Optional[float]
    current_question: int
    answers: Dict[int, str]  # question_id -> code
    status: str  # "active", "completed", "timeout"


@dataclass
class ExamResult:
    """Represents exam results"""
    session_id: str
    student_id: str
    exam_id: str
    score: int
    total_questions: int
    completion_time: float
    ended_reason: str  # "completed", "timeout", "manual"
    timestamp: float


class IExamServer(ABC):
    """Remote interface for exam servers"""

    @abstractmethod
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and status"""
        pass

    @abstractmethod
    def create_exam(self, exam_data: Dict[str, Any]) -> bool:
        """Create a new exam"""
        pass

    @abstractmethod
    def start_exam_session(self, student_id: str, exam_id: str) -> Optional[ExamSession]:
        """Start a new exam session for a student"""
        pass

    @abstractmethod
    def submit_answer(self, session_id: str, question_id: int, code: str) -> Dict[str, Any]:
        """Submit code for a specific question"""
        pass

    @abstractmethod
    def get_exam_results(self) -> List[ExamResult]:
        """Get all exam results from this server"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Health check endpoint"""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics (load, active sessions, etc.)"""
        pass


class ILoadBalancer(ABC):
    """Remote interface for load balancer"""

    @abstractmethod
    def register_server(self, server_info: Dict[str, Any]) -> bool:
        """Register a new exam server"""
        pass

    @abstractmethod
    def unregister_server(self, server_id: str) -> bool:
        """Unregister an exam server"""
        pass

    @abstractmethod
    def get_best_server(self) -> Optional[Dict[str, Any]]:
        """Get the best server for load balancing"""
        pass

    @abstractmethod
    def update_server_metrics(self, server_id: str, metrics: Dict[str, Any]) -> bool:
        """Update server metrics"""
        pass


class IRegistry(ABC):
    """Remote interface for service registry"""

    @abstractmethod
    def register_service(self, service_name: str, service_info: Dict[str, Any]) -> bool:
        """Register a service in the registry"""
        pass

    @abstractmethod
    def unregister_service(self, service_name: str, service_id: str) -> bool:
        """Unregister a service"""
        pass

    @abstractmethod
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover services by name"""
        pass

    @abstractmethod
    def get_all_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered services"""
        pass


class ILeaderElection(ABC):
    """Remote interface for leader election"""

    @abstractmethod
    def start_election(self, server_id: str, priority: int) -> bool:
        """Start leader election process"""
        pass

    @abstractmethod
    def announce_leader(self, leader_id: str, timestamp: float) -> bool:
        """Announce new leader"""
        pass

    @abstractmethod
    def get_leader(self) -> Optional[Dict[str, Any]]:
        """Get current leader information"""
        pass

    @abstractmethod
    def is_leader(self, server_id: str) -> bool:
        """Check if server is current leader"""
        pass


class IDataReplication(ABC):
    """Remote interface for data replication"""

    @abstractmethod
    def replicate_data(self, data: Dict[str, Any], operation: str) -> bool:
        """Replicate data to other servers"""
        pass

    @abstractmethod
    def sync_data(self, server_id: str) -> Dict[str, Any]:
        """Sync data with a specific server"""
        pass

    @abstractmethod
    def resolve_conflict(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve data conflicts using vector clocks"""
        pass
