CREATE TABLE public.impact_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rca_run_id uuid NOT NULL REFERENCES public.rca_runs(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    analysis_version text NOT NULL
        CHECK (btrim(analysis_version) <> '' AND length(analysis_version) <= 64),
    input_fingerprint text NOT NULL
        CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
    topology_fingerprint text NOT NULL
        CHECK (topology_fingerprint ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN ('ASSESSED', 'INCONCLUSIVE')),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_analyzed_at timestamptz NOT NULL DEFAULT now(),
    CHECK (last_analyzed_at >= created_at),
    UNIQUE (rca_run_id, analysis_version, input_fingerprint)
);
CREATE INDEX impact_runs_rca_latest_idx
    ON public.impact_runs (rca_run_id, last_analyzed_at DESC, id DESC);
ALTER TABLE public.impact_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.impact_runs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.impact_runs TO service_role;
