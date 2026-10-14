CREATE TABLE public.incident_anomalies (
    incident_id uuid NOT NULL REFERENCES public.incidents(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    anomaly_id uuid NOT NULL REFERENCES public.anomalies(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    relationship_type text NOT NULL CHECK (btrim(relationship_type) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (incident_id, anomaly_id),
    UNIQUE (anomaly_id)
);
CREATE INDEX incident_anomalies_incident_idx
    ON public.incident_anomalies (incident_id, created_at);
ALTER TABLE public.incident_anomalies ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.incident_anomalies FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.incident_anomalies TO service_role;
