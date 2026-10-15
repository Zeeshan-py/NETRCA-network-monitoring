"""Validate Gemini's selection and render only server-authored grounded claims."""
from app.explanation.context import build_input
from app.explanation.models import Explanation, SourceReference
from app.explanation.provider import GeminiProvider
from app.explanation.store import ExplanationStore


class ExplanationService:
    def __init__(self, store: ExplanationStore, provider: GeminiProvider):
        self.store = store
        self.provider = provider

    def explain(self, incident_id):
        context = build_input(self.store.load(incident_id))
        selection = self.provider.select(context)
        by_id = {claim.claim_id: claim for claim in context.claims}
        ordered = [by_id[claim_id] for claim_id in selection.ordered_claim_ids]
        categories = {name: [claim for claim in ordered if claim.section == name] for name in (
            "summary", "observed_facts", "candidate_explanations", "failure_chain_explanation",
            "impact_explanation", "uncertainties", "missing_evidence", "limitations")}
        refs: dict[tuple, SourceReference] = {}
        for claim in ordered:
            for ref in claim.evidence_references:
                refs[(ref.source_type, ref.source_id, ref.timestamp)] = ref
        return Explanation(incident_id=context.incident_id, rca_run_id=context.rca_run_id,
                           impact_run_id=context.impact_run_id,
                           model_name=self.provider.settings.gemini_model,
                           evidence_references=list(refs.values()), **categories)
