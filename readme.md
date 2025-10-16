## Distributed Exam Platform (Flask)

This project provides:
- A pool of backend exam servers (`exam_server.py`) with capacity limits
- A Flask load balancer (`load_balancer.py`) with health checks and least-connections routing
- A simple web UI (teacher + student) served by the load balancer
- A CLI client (`client_cli.py`) as an alternative to the web UI

### Requirements

Install Python 3.10+ and the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the backend exam servers

Open three terminals and run one per server (or adjust as needed):

```bash
python exam_server.py 6001 S1
```

```bash
python exam_server.py 6002 S2
```

```bash
python exam_server.py 6003 S3
```

### Running the load balancer + Web UI

In a new terminal:

```bash
python load_balancer.py
```

The web UI will be at `http://localhost:5555`.

### Teacher flow

1. Go to `http://localhost:5555/teacher`
2. Fill in title, duration, capacity, and provide questions JSON, e.g.:

```json
[
  {"id": 1, "question": "Which keyword is used to inherit a class in Java?", "options": ["A) this", "B) super", "C) extends", "D) implements"], "answer": "C"},
  {"id": 2, "question": "Which of these is not a Java primitive type?", "options": ["A) int", "B) float", "C) boolean", "D) string"], "answer": "D"}
]
```

3. Submit to push the configuration to all healthy servers.

### Student flow (Web)

1. Go to `http://localhost:5555/student`
2. You should see available exams aggregated from the healthy servers
3. Enter a username and Start Exam
4. Answer questions on the `student_exam` page until you finish; results are displayed

### CLI client (optional)

```bash
python client_cli.py
```

### Notes

- The load balancer implements least-connections routing and sticky sessions via a `SESSION_MAP` so that subsequent answers go to the same backend server.
- Health checks and metrics are used to determine server health and load.


