"""Run a bounded AI-agent loop with a fresh context on every iteration."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "build"))
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--start-at", type=int, default=1)
    args = parser.parse_args()

    if args.iterations < 1:
        parser.error("--iterations must be at least 1")
    if args.start_at < 1 or args.start_at > args.iterations:
        parser.error("--start-at must be between 1 and --iterations")

    prompt_path = ROOT / "agent_prompts" / f"base-{args.mode}-loop.txt"
    base_prompt = prompt_path.read_text(encoding="utf-8")
    log_dir = ROOT / "loop_logs"
    log_dir.mkdir(exist_ok=True)

    for iteration in range(args.start_at, args.iterations + 1):
        wrapper = f"""

LOOP ITERATION {iteration} OF {args.iterations}
This is a fresh agent context. Read the repository artifacts before acting.
Continue from the current repository state; do not redo completed work.
Do not run git commit or git push. The supervising human commits after the
whole stage. End your final response with LOOP_COMPLETE only if this stage is
fully complete and verified; otherwise end with LOOP_CONTINUE.
"""
        exact_prompt = base_prompt.rstrip() + wrapper
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
        result = subprocess.run(
            [
                npx,
                "-y",
                "@openai/codex@0.144.1",
                "exec",
                "-C",
                str(ROOT),
                "--sandbox",
                "workspace-write",
                "--ephemeral",
                "-",
            ],
            cwd=ROOT,
            input=exact_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        log_path = log_dir / f"base-{args.mode}-codex-iteration-{iteration:02d}.txt"
        log_path.write_text(
            "\n".join(
                [
                    f"started_utc: {started}",
                    f"mode: {args.mode}",
                    "runner: OpenAI Codex CLI 0.144.1",
                    f"iteration: {iteration}",
                    f"return_code: {result.returncode}",
                    "",
                    "===== EXACT PROMPT =====",
                    exact_prompt,
                    "",
                    "===== AGENT OUTPUT =====",
                    result.stdout,
                    "",
                    "===== STDERR =====",
                    result.stderr,
                ]
            ),
            encoding="utf-8",
        )
        print(f"Iteration {iteration}: return code {result.returncode}")
        print(result.stdout.strip())
        if result.returncode != 0:
            return result.returncode
        if args.mode == "build" and "LOOP_COMPLETE" in result.stdout:
            print("Agent reported stage completion.")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
