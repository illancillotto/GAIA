"""Explicit opt-in live comparison; no documentation corpus input is accepted."""

import argparse
import asyncio
from pathlib import Path

from .context import CallContext
from .data.service import DataService
from .experiment_cases import synthetic_cases
from .experiment_runner import (
    ComparisonExecutor,
    ExperimentConfig,
    experiment_manifest,
    run_comparison,
    schedule,
)
from .experiment_static import EXPERIMENT_SCOPES, SyntheticStaticCorpus
from .routes import model_client, source_client


async def live(cases, corpus, config, output):
    async with model_client() as model:
        executor = ComparisonExecutor(source_client(), model, corpus, config)
        return await run_comparison(cases, executor, output)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Synthetic-only static RAG vs Wiki MCP")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    config = ExperimentConfig(seed=args.seed, repeats=args.repeats)
    service = DataService(args.database)
    try:
        cases = synthetic_cases(service)
        if not args.live:
            import json

            print(
                json.dumps(
                    {
                        "manifest": experiment_manifest(
                            cases, service.manifest["dataset_version"], config
                        ),
                        "schedule": schedule(cases, config),
                    }
                )
            )
            return
        corpus = SyntheticStaticCorpus(
            service, CallContext(principal="synthetic-comparison", scopes=EXPERIMENT_SCOPES)
        )
        try:
            records = asyncio.run(live(cases, corpus, config, args.output))
            print(
                f"Completed: {sum(row['status'] == 'completed' for row in records)}; attempts: {len(records)}"
            )
        finally:
            corpus.close()
    finally:
        service.close()


if __name__ == "__main__":
    main()
