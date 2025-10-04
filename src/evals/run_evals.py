"""
Run evaluations for the Discord bot router and personas.

Usage:
    # Run all evals with default (baseline) model
    uv run src/evals/run_evals.py

    # Run specific eval dataset
    uv run src/evals/run_evals.py --dataset router_persona_selection

    # Run with different model
    uv run src/evals/run_evals.py --model llama3.1-70b

    # Run and save results as new baseline
    uv run src/evals/run_evals.py --save-baseline

    # Compare against baseline
    uv run src/evals/run_evals.py --compare-to-baseline
"""

import argparse
import asyncio
from pathlib import Path
from typing import Any

from pydantic_evals import Dataset
import logfire
from dotenv import load_dotenv

from discord_hack.agent import create_router_agent
from discord_hack.router import RouterContext, RouterDecision, build_router_prompt

from evals.config import DATASETS_DIR, MODEL_CONFIGS
from evals.evaluators.router_evaluators import (
    ContextSelectionEvaluator,
    ConversationRoutingEvaluator,
    PersonaSuggestionEvaluator,
    StructuredOutputEvaluator,
)
from evals.evaluators.persona_evaluators import PersonaResponseFormatEvaluator

# Dataset registry
EVAL_DATASETS = {
    "router_persona_selection": DATASETS_DIR / "router_persona_selection.yaml",
    "router_context_selection": DATASETS_DIR / "router_context_selection.yaml",
    "router_conversation_routing": DATASETS_DIR / "router_conversation_routing.yaml",
    "router_structured_output": DATASETS_DIR / "router_structured_output.yaml",
    "router_response_format": DATASETS_DIR / "router_response_format.yaml",
}


async def run_router_eval(
    dataset_path: Path,
    model_config: dict[str, Any],
) -> Any:
    """Run router evaluation with specified model config.

    Args:
        dataset_path: Path to the YAML dataset file
        model_config: Dictionary with model configuration (model name, temperature, etc.)

    Returns:
        Evaluation report object
    """
    # Load dataset with custom evaluators
    custom_evaluators = [
        PersonaSuggestionEvaluator,
        StructuredOutputEvaluator,
        ContextSelectionEvaluator,
        ConversationRoutingEvaluator,
        PersonaResponseFormatEvaluator,
    ]
    dataset = Dataset[RouterContext, RouterDecision, dict].from_file(
        dataset_path, custom_evaluator_types=custom_evaluators
    )

    # Create router agent with model config
    router_agent = create_router_agent(
        model_name=model_config["model"],
        temperature=model_config.get("temperature", 0.0),
    )

    # Define task function
    async def router_task(ctx: RouterContext) -> RouterDecision:
        """Task function: run router on input context."""
        # Build the same prompt format that the actual bot uses
        router_prompt = build_router_prompt(
            ctx.current_message, ctx.active_conversations
        )

        decision = await router_agent.run(
            router_prompt,
            deps=ctx,
        )
        return decision.output

    # Run evaluation with max_concurrency=1 to avoid rate limiting
    # Cerebras free tier: 30 req/min, 60k tokens/min
    with logfire.span(
        "eval_run",
        dataset=dataset_path.stem,
        model=model_config["model"],
    ):
        report = await dataset.evaluate(router_task, max_concurrency=1)

    # Print results
    print(f"\n{'=' * 80}")
    print(f"Evaluation: {dataset_path.stem}")
    print(f"Model: {model_config['model']}")
    print(f"{'=' * 80}\n")
    report.print(include_input=False, include_output=False)

    return report


def main() -> None:
    """Main entry point for eval runner."""
    parser = argparse.ArgumentParser(description="Run Discord bot evaluations")
    _ = parser.add_argument(
        "--dataset",
        choices=list(EVAL_DATASETS.keys()) + ["all"],
        default="all",
        help="Which dataset to evaluate",
    )
    _ = parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIGS.keys()),
        default="baseline",
        help="Which model configuration to use",
    )
    _ = parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save results as new baseline",
    )
    _ = parser.add_argument(
        "--compare-to-baseline",
        action="store_true",
        help="Compare results to saved baseline",
    )

    args = parser.parse_args()

    _ = load_dotenv()
    _ = logfire.configure(
        send_to_logfire="if-token-present",
        environment="evals",
        service_name="discord-bot-evals",
    )

    # Determine which datasets to run
    if args.dataset == "all":
        datasets_to_run = EVAL_DATASETS.items()
    else:
        datasets_to_run = [(args.dataset, EVAL_DATASETS[args.dataset])]

    model_config = MODEL_CONFIGS[args.model]

    # Run evaluations
    for dataset_name, dataset_path in datasets_to_run:
        if not dataset_path.exists():
            print(f"⚠️  Dataset not found: {dataset_path}")
            continue

        if "router" in dataset_name:
            asyncio.run(run_router_eval(dataset_path, model_config))
        else:
            print(f"⚠️  Unknown dataset type: {dataset_name}")


if __name__ == "__main__":
    main()
