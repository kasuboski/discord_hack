from pathlib import Path

# Eval configuration
EVALS_DIR = Path(__file__).parent
DATASETS_DIR = EVALS_DIR / "datasets"
RESULTS_DIR = EVALS_DIR / "results"  # Store baseline results

# Model configurations to test
MODEL_CONFIGS = {
    "baseline": {
        "model": "llama3.1-8b",
        "temperature": 0.3,  # Deterministic for evals
    },
    "llama3.3-70b": {
        "model": "llama3.3-70b",
        "temperature": 0.0,
    },
    "llama4-scout": {
        "model": "llama-4-scout-17b-16e-instruct",
        "temperature": 0.0,
    },
}
