"""Router evaluators for testing LLM-based conversation routing.

These evaluators validate that the router makes correct decisions about:
1. Persona selection - Which persona should respond
2. Context selection - Which messages are relevant for context
3. Conversation routing - Which conversation the message belongs to
4. Structured output - Valid RouterDecision structure
"""

from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from discord_hack.router import RouterContext, RouterDecision


@dataclass
class PersonaSuggestionEvaluator(Evaluator):
    """Checks if router suggested the expected persona."""

    def evaluate(self, ctx: EvaluatorContext[RouterContext, RouterDecision]) -> dict:
        # Ensure we have valid data to evaluate
        assert ctx.output is not None, "Router output is None"
        assert ctx.expected_output is not None, "Expected output is None"

        expected_persona = ctx.expected_output.suggested_persona
        actual_persona = ctx.output.suggested_persona

        return {
            "persona_match": expected_persona == actual_persona,
            "confidence": ctx.output.confidence,
            "reasoning_quality": len(ctx.output.reasoning) > 20,  # Has reasoning
        }


@dataclass
class ContextSelectionEvaluator(Evaluator):
    """Validates router selected the right context messages."""

    def evaluate(self, ctx: EvaluatorContext[RouterContext, RouterDecision]) -> dict:
        # Ensure we have valid data to evaluate
        assert ctx.output is not None, "Router output is None"
        assert ctx.expected_output is not None, "Expected output is None"

        expected_ids = set(ctx.expected_output.relevant_message_ids)
        actual_ids = set(ctx.output.relevant_message_ids)

        # Calculate precision/recall
        true_positives = len(expected_ids & actual_ids)

        precision = true_positives / len(actual_ids) if actual_ids else 0
        recall = true_positives / len(expected_ids) if expected_ids else 0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "exact_match": expected_ids == actual_ids,
        }


@dataclass
class ConversationRoutingEvaluator(Evaluator):
    """Validates router routes to correct conversation."""

    def evaluate(self, ctx: EvaluatorContext[RouterContext, RouterDecision]) -> dict:
        # Ensure we have valid data to evaluate
        assert ctx.output is not None, "Router output is None"
        assert ctx.expected_output is not None, "Expected output is None"

        expected_conv_id = ctx.expected_output.conversation_id
        actual_conv_id = ctx.output.conversation_id

        # Exact match for conversation routing
        conv_match = expected_conv_id == actual_conv_id

        # Check confidence is appropriate
        if expected_conv_id is not None:
            # Existing conversation: should have high confidence
            confidence_appropriate = ctx.output.confidence >= 0.6
        else:
            # New conversation: lower confidence expected
            confidence_appropriate = ctx.output.confidence < 0.7

        return {
            "conversation_match": conv_match,
            "confidence_appropriate": confidence_appropriate,
            "confidence": ctx.output.confidence,
        }


@dataclass
class StructuredOutputEvaluator(Evaluator):
    """Validates RouterDecision output structure."""

    def evaluate(self, ctx: EvaluatorContext[RouterContext, RouterDecision]) -> dict:
        output = ctx.output
        router_ctx = ctx.inputs

        # Check all message IDs are valid
        all_message_ids = set()
        for conv in router_ctx.active_conversations:
            all_message_ids.update(msg.id for msg in conv.messages)

        valid_message_ids = all(
            msg_id in all_message_ids for msg_id in output.relevant_message_ids
        )

        # Check persona is valid
        available_persona_names = [p.name for p in router_ctx.available_personas]
        valid_persona = (
            output.suggested_persona is None
            or output.suggested_persona in available_persona_names
        )

        # Check conversation_id is valid
        valid_conv_id = output.conversation_id is None or any(
            conv.id == output.conversation_id
            for conv in router_ctx.active_conversations
        )

        return {
            "is_pydantic_model": isinstance(output, RouterDecision),
            "confidence_in_bounds": 0.0 <= output.confidence <= 1.0,
            "has_reasoning": len(output.reasoning) > 0,
            "valid_message_ids": valid_message_ids,
            "valid_persona": valid_persona,
            "valid_conversation_id": valid_conv_id,
            "should_respond_matches_mention": (
                not router_ctx.is_bot_mentioned or output.should_respond
            ),
        }
