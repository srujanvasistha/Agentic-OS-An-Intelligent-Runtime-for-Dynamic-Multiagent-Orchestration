import random
import json
from dataclasses import asdict
from workload.task import Task


TASK_TYPES = [
    "compute",
    "io",
    "network",
    "data",
    "ml",
    "text",
    "delay"
]

COMPLEXITIES = [
    "low",
    "medium",
    "high"
]


TASK_PAYLOADS = {
    "compute": [
        {
            "operation": "matrix_multiplication",
            "size": 500
        },
        {
            "operation": "prime_generation",
            "limit": 100000
        },
        {
            "operation": "sorting",
            "items": 10000
        }
    ],

    "io": [
        {
            "operation": "file_read",
            "file_size_mb": 10
        },
        {
            "operation": "file_write",
            "file_size_mb": 20
        },
        {
            "operation": "json_processing",
            "records": 5000
        }
    ],

    "network": [
        {
            "operation": "api_request",
            "endpoint": "/api/users"
        },
        {
            "operation": "data_fetch",
            "source": "remote_server"
        },
        {
            "operation": "health_check",
            "service": "database"
        }
    ],

    "data": [
        {
            "operation": "data_cleaning",
            "records": 10000
        },
        {
            "operation": "data_transformation",
            "columns": 15
        },
        {
            "operation": "aggregation",
            "groups": 50
        }
    ],

    "ml": [
        {
            "operation": "classification",
            "samples": 5000
        },
        {
            "operation": "prediction",
            "samples": 1000
        },
        {
            "operation": "feature_processing",
            "features": 50
        }
    ],

    "text": [
        {
            "operation": "tokenization",
            "words": 10000
        },
        {
            "operation": "text_analysis",
            "documents": 500
        },
        {
            "operation": "keyword_extraction",
            "documents": 100
        }
    ],

    "delay": [
        {
            "operation": "simulated_delay",
            "seconds": 2
        },
        {
            "operation": "simulated_delay",
            "seconds": 5
        },
        {
            "operation": "simulated_delay",
            "seconds": 8
        }
    ]
}


def generate_workload(num_tasks=40, seed=42):

    random.seed(seed)

    workload = []

    # Ensure every task type appears
    base_types = TASK_TYPES.copy()

    remaining = num_tasks - len(base_types)

    task_types = base_types + random.choices(
        TASK_TYPES,
        k=remaining
    )

    random.shuffle(task_types)

    for i, task_type in enumerate(task_types, start=1):

        priority = random.randint(1, 5)

        complexity = random.choice(COMPLEXITIES)

        payload = random.choice(
            TASK_PAYLOADS[task_type]
        )

        estimated_duration = round(
            random.uniform(1.0, 10.0),
            2
        )

        task = Task(
            task_id=f"TASK-{i:03d}",
            task_type=task_type,
            priority=priority,
            complexity=complexity,
            payload=payload,
            estimated_duration=estimated_duration
        )

        workload.append(task)

    return workload


def print_workload_summary(workload):

    summary = {}

    for task in workload:
        summary[task.task_type] = (
            summary.get(task.task_type, 0) + 1
        )

    print("\nWorkload Summary")
    print("----------------------------------------")

    for task_type in sorted(summary):
        print(
            f"{task_type:<10}: "
            f"{summary[task_type]}"
        )

    print("----------------------------------------")
    print(f"Total      : {len(workload)}")


def save_workload(workload, filename="workload/workload.json"):

    workload_data = [
        asdict(task)
        for task in workload
    ]

    with open(filename, "w") as file:
        json.dump(
            workload_data,
            file,
            indent=4
        )

    print(f"\nWorkload saved to: {filename}")


if __name__ == "__main__":

    workload = generate_workload(
        num_tasks=40,
        seed=42
    )

    print("\nGenerated Tasks")
    print("=" * 70)

    for task in workload:

        print(
            f"{task.task_id} | "
            f"type={task.task_type:<8} | "
            f"priority={task.priority} | "
            f"complexity={task.complexity:<6} | "
            f"operation={task.payload['operation']:<25} | "
            f"status={task.status}"
        )

    print_workload_summary(workload)

    save_workload(workload)