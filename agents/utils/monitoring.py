"""Monitoring utilities for agent evaluation and tracking."""
from typing import Any, Dict, Optional
import uuid
from langsmith import Client
from langsmith.evaluation import RunEvaluator
from langsmith.schemas import Example, Run

from ..config.langsmith import client

class DeckBuilderEvaluator(RunEvaluator):
    """Evaluator for deck builder agent outputs."""
    
    async def evaluate_run(
        self, run: Run, example: Optional[Example] = None
    ) -> Dict[str, Any]:
        """Evaluate a single run of the deck builder agent."""
        metrics = {
            "completion_rate": 1.0 if run.end_time else 0.0,
            "error_occurred": run.error is not None,
        }
        
        # Add specific metrics for deck building tasks
        if run.outputs:
            outputs = run.outputs
            metrics.update({
                "has_slides": "slides" in outputs,
                "has_script": "script" in outputs,
                "validation_passed": outputs.get("validation_passed", False)
            })
        
        return metrics

def create_dataset_example(
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    dataset_name: str = "deck-builder-examples"
) -> None:
    """Create a dataset example for evaluation."""
    client.create_dataset(dataset_name=dataset_name, description="Examples for deck builder evaluation")
    client.create_example(
        inputs=input_data,
        outputs=output_data,
        dataset_name=dataset_name
    )

def log_run_metrics(
    name: str,
    metrics: Dict[str, Any],
    run_id: Optional[str] = None
) -> None:
    """Log custom metrics for a run."""
    # Generate a UUID if one isn't provided
    run_id = run_id or str(uuid.uuid4())
    
    # Add the name as a tag
    metrics["name"] = name
    
    # Update run synchronously since we're using it in an async context
    client.update_run(
        run_id=run_id,
        feedback=metrics
    ) 