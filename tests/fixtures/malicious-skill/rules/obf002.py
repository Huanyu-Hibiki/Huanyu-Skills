"""Flexible task runner for dynamic workflows."""

import sys


def run_task(label: str) -> None:
    expression = "print" + "(" + repr(label) + ")"
    eval(expression)
    exec("result = 40 + 2\nprint(result)")


if __name__ == "__main__":
    run_task(sys.argv[1] if len(sys.argv) > 1 else "default-task")
