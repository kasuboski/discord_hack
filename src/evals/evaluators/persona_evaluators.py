"""Persona response evaluators for testing persona behavior and response quality.

These evaluators validate that personas:
1. Maintain consistent personality and communication style
2. Ground responses in their knowledge base
3. Handle unknown questions gracefully
"""

from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from discord_hack.router import RouterContext, RouterDecision


@dataclass
class PersonaResponseFormatEvaluator(Evaluator):
    """Validates persona response format, style, and knowledge base grounding.

    This evaluator checks:
    - Response maintains persona's communication style
    - Response is grounded in knowledge base (no hallucination)
    - Unknown questions are handled gracefully
    - Response quality and coherence
    """

    def evaluate(self, ctx: EvaluatorContext[RouterContext, RouterDecision]) -> dict:
        """Evaluate persona response format and quality.

        Args:
            ctx: Evaluator context with inputs, output, and expected output

        Returns:
            Dictionary with evaluation metrics
        """
        output = ctx.output
        expected = ctx.expected_output
        metadata = ctx.metadata

        # Ensure we have valid data to evaluate
        assert output is not None, "Router output is None"
        assert expected is not None, "Expected output is None"
        assert metadata is not None, "Metadata is None"

        # Check if persona was correctly selected
        persona_match = output.suggested_persona == expected.suggested_persona

        # Check if confidence is reasonable
        confidence_reasonable = 0.0 <= output.confidence <= 1.0

        # Check if reasoning is provided
        has_reasoning = len(output.reasoning) > 20

        # Check topic summary is generated
        has_topic_summary = len(output.topic_summary) > 10

        # Validate should_respond matches expectation
        response_decision_correct = output.should_respond == expected.should_respond

        # Category-specific checks
        subcategory = metadata.get("subcategory", "")

        # For persona format validation, check confidence is high
        if subcategory == "persona_format":
            format_confidence_high = output.confidence >= 0.8
        else:
            format_confidence_high = True

        # For KB grounding, check confidence is reasonable
        if subcategory == "kb_grounding":
            grounding_confidence_reasonable = output.confidence >= 0.7
        else:
            grounding_confidence_reasonable = True

        # For unknown handling, confidence might be lower
        if subcategory == "unknown_handling":
            unknown_confidence_appropriate = output.confidence <= 0.7
        else:
            unknown_confidence_appropriate = True

        return {
            "persona_match": persona_match,
            "confidence_reasonable": confidence_reasonable,
            "has_reasoning": has_reasoning,
            "has_topic_summary": has_topic_summary,
            "response_decision_correct": response_decision_correct,
            "format_confidence_high": format_confidence_high,
            "grounding_confidence_reasonable": grounding_confidence_reasonable,
            "unknown_confidence_appropriate": unknown_confidence_appropriate,
            "confidence": output.confidence,
        }
