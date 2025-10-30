# Distributed Coding Exam Platform

A comprehensive distributed system for conducting coding exams with advanced features including RMI, logical clocks, leader election, data consistency, replication, and load balancing.

## Architecture

### Components
1. **Registry Server** - RMI registry for service discovery
2. **Exam Servers** - Multiple instances handling coding exams
3. **Load Balancer** - Distributes requests across exam servers
4. **Teacher Dashboard** - Web interface for exam management
5. **Student Interface** - Web interface for taking exams
6. **Code Execution Engine** - Validates student code submissions

### Features
- **RMI Communication** - Remote method invocation between components
- **Logical Clocks** - Lamport timestamps for event ordering
- **Leader Election** - Bully algorithm for coordinator selection
- **Data Consistency** - Eventual consistency with conflict resolution
- **Replication** - Data replication across multiple servers
- **Load Balancing** - Least connections strategy
- **Code Validation** - LeetCode-style problem validation
- **Real-time IDE** - Code editor with syntax highlighting

## Quick Start

1. Start the registry server:
```bash
python registry_server.py
```

2. Start exam servers:
```bash
python exam_server.py 6001 S1
python exam_server.py 6002 S2
python exam_server.py 6003 S3
```

3. Start load balancer:
```bash
python load_balancer.py
```

4. Access the platform:
- Teacher Dashboard: http://localhost:5555/teacher
- Student Interface: http://localhost:5555/student

## Technology Stack
- Python 3.8+
- Flask (Web Framework)
- Pyro4 (RMI Implementation)
- SQLite (Database)
- Docker (Containerization)
- HTML/CSS/JavaScript (Frontend)
