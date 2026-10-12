-- NetRCA Phase 2. Applied once through Supabase migration history.
-- All references restrict deletion/update to preserve historical observations.
CREATE TABLE public.devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
    device_type text NOT NULL CHECK (device_type IN ('ROUTER','SWITCH','SERVER','HOST','DNS')),
    ip_address inet UNIQUE,
    mac_address text,
    hostname text,
    status text NOT NULL CHECK (status IN ('HEALTHY','WARNING','DOWN')),
    is_active boolean NOT NULL DEFAULT true,
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_device_id uuid NOT NULL REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    destination_device_id uuid NOT NULL REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    bandwidth_mbps numeric CHECK (bandwidth_mbps >= 0 AND bandwidth_mbps < 'Infinity'::numeric),
    latency_ms numeric CHECK (latency_ms >= 0 AND latency_ms < 'Infinity'::numeric),
    packet_loss_percent numeric CHECK (packet_loss_percent BETWEEN 0 AND 100),
    status text NOT NULL CHECK (status IN ('UP','DEGRADED','DOWN')),
    interface_source text,
    interface_destination text,
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source_device_id <> destination_device_id)
);

CREATE TABLE public.services (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (btrim(name) <> ''),
    service_type text NOT NULL CHECK (btrim(service_type) <> ''),
    port integer CHECK (port BETWEEN 1 AND 65535),
    protocol text,
    status text NOT NULL CHECK (status IN ('UP','DEGRADED','DOWN')),
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.device_services (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid NOT NULL REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    service_id uuid NOT NULL REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    status text NOT NULL CHECK (status IN ('UP','DEGRADED','DOWN')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (device_id, service_id)
);

CREATE TABLE public.metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    link_id uuid REFERENCES public.links ON DELETE RESTRICT ON UPDATE RESTRICT,
    metric_type text NOT NULL CHECK (metric_type IN ('LATENCY','PACKET_LOSS','BANDWIDTH','THROUGHPUT','CPU','MEMORY','ERROR_RATE','AVAILABILITY')),
    value numeric NOT NULL CHECK (value >= 0 AND value < 'Infinity'::numeric),
    unit text,
    expected_value numeric CHECK (expected_value >= 0 AND expected_value < 'Infinity'::numeric),
    timestamp timestamptz NOT NULL,
    metadata jsonb,
    CHECK (num_nonnulls(device_id, link_id) >= 1),
    CHECK (metric_type NOT IN ('PACKET_LOSS','CPU','MEMORY','AVAILABILITY') OR value <= 100),
    CHECK (metric_type NOT IN ('PACKET_LOSS','CPU','MEMORY','AVAILABILITY') OR expected_value <= 100)
);

CREATE TABLE public.logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    -- SRS FR-007/data requirements also allow service-originated logs.
    service_id uuid REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    severity text NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR','CRITICAL')),
    event_type text,
    message text NOT NULL CHECK (btrim(message) <> ''),
    source text,
    timestamp timestamptz NOT NULL,
    metadata jsonb,
    CHECK (num_nonnulls(device_id, service_id) >= 1)
);

CREATE TABLE public.events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    link_id uuid REFERENCES public.links ON DELETE RESTRICT ON UPDATE RESTRICT,
    service_id uuid REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    event_type text NOT NULL CHECK (btrim(event_type) <> ''),
    severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    metric_type text,
    observed_value numeric CHECK (observed_value > '-Infinity'::numeric AND observed_value < 'Infinity'::numeric),
    expected_value numeric CHECK (expected_value > '-Infinity'::numeric AND expected_value < 'Infinity'::numeric),
    message text,
    status text NOT NULL CHECK (status IN ('DETECTED','ACKNOWLEDGED','RESOLVED')),
    timestamp timestamptz NOT NULL,
    metadata jsonb
);

CREATE TABLE public.anomalies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    metric_id uuid REFERENCES public.metrics ON DELETE RESTRICT ON UPDATE RESTRICT,
    event_id uuid REFERENCES public.events ON DELETE RESTRICT ON UPDATE RESTRICT,
    model_name text NOT NULL CHECK (btrim(model_name) <> ''),
    model_version text,
    anomaly_score numeric NOT NULL CHECK (anomaly_score BETWEEN 0 AND 1),
    is_anomaly boolean NOT NULL,
    severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    detected_at timestamptz NOT NULL,
    features jsonb,
    metadata jsonb,
    CHECK (num_nonnulls(device_id, metric_id, event_id) >= 1)
);

CREATE TABLE public.incidents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL CHECK (btrim(title) <> ''),
    description text,
    severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status text NOT NULL CHECK (status IN ('DETECTED','INVESTIGATING','ROOT_CAUSE_IDENTIFIED','RESOLVED','CLOSED')),
    start_time timestamptz NOT NULL,
    end_time timestamptz,
    root_cause_summary text,
    confidence numeric CHECK (confidence BETWEEN 0 AND 1),
    impact_summary text,
    ai_summary text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_time >= start_time),
    CHECK (status NOT IN ('RESOLVED','CLOSED') OR end_time IS NOT NULL)
);

CREATE TABLE public.incident_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents ON DELETE RESTRICT ON UPDATE RESTRICT,
    event_id uuid NOT NULL REFERENCES public.events ON DELETE RESTRICT ON UPDATE RESTRICT,
    sequence_number integer NOT NULL CHECK (sequence_number > 0),
    relationship_type text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (incident_id, event_id),
    UNIQUE (incident_id, sequence_number)
);

CREATE TABLE public.root_causes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents ON DELETE RESTRICT ON UPDATE RESTRICT,
    cause_type text NOT NULL CHECK (btrim(cause_type) <> ''),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    link_id uuid REFERENCES public.links ON DELETE RESTRICT ON UPDATE RESTRICT,
    service_id uuid REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    description text NOT NULL CHECK (btrim(description) <> ''),
    confidence numeric NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    analysis_method text NOT NULL CHECK (btrim(analysis_method) <> ''),
    identified_at timestamptz NOT NULL,
    metadata jsonb,
    UNIQUE (incident_id, id)
);

CREATE TABLE public.root_cause_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    root_cause_id uuid NOT NULL REFERENCES public.root_causes ON DELETE RESTRICT ON UPDATE RESTRICT,
    source_type text NOT NULL CHECK (source_type IN ('METRIC','LOG','EVENT','ANOMALY','TOPOLOGY')),
    source_id uuid NOT NULL,
    description text NOT NULL CHECK (btrim(description) <> ''),
    importance text CHECK (importance IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    timestamp timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (root_cause_id, source_type, source_id)
);

CREATE TABLE public.impact_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents ON DELETE RESTRICT ON UPDATE RESTRICT,
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    link_id uuid REFERENCES public.links ON DELETE RESTRICT ON UPDATE RESTRICT,
    service_id uuid REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    impact_type text NOT NULL CHECK (impact_type IN ('DEVICE_AFFECTED','LINK_AFFECTED','SERVICE_AFFECTED','LATENCY_DEGRADATION','PACKET_LOSS','AVAILABILITY_LOSS','REQUEST_FAILURE')),
    severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    description text,
    detected_at timestamptz NOT NULL,
    resolved_at timestamptz,
    metadata jsonb,
    CHECK (num_nonnulls(device_id, link_id, service_id) >= 1),
    CHECK (resolved_at >= detected_at)
);

CREATE TABLE public.recommendations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents ON DELETE RESTRICT ON UPDATE RESTRICT,
    root_cause_id uuid,
    title text NOT NULL CHECK (btrim(title) <> ''),
    description text NOT NULL CHECK (btrim(description) <> ''),
    priority text NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    source text NOT NULL CHECK (source IN ('RULE','RCA_ENGINE','GEMINI')),
    confidence numeric CHECK (confidence BETWEEN 0 AND 1),
    status text NOT NULL CHECK (status IN ('PENDING','REVIEWED','APPLIED','DISMISSED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (incident_id, root_cause_id) REFERENCES public.root_causes (incident_id, id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE public.ai_analyses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents ON DELETE RESTRICT ON UPDATE RESTRICT,
    analysis_type text NOT NULL CHECK (analysis_type IN ('INCIDENT_EXPLANATION','RCA_EXPLANATION','IMPACT_SUMMARY','RECOMMENDATION','INCIDENT_REPORT')),
    model_name text NOT NULL CHECK (btrim(model_name) <> ''),
    prompt_version text,
    input_context jsonb,
    output_text text NOT NULL CHECK (btrim(output_text) <> ''),
    structured_output jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.fault_injections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fault_type text NOT NULL CHECK (fault_type IN ('ROUTER_FAILURE','INTERFACE_FAILURE','SWITCH_FAILURE','LINK_FAILURE','PACKET_LOSS','HIGH_LATENCY','CONGESTION','DNS_FAILURE','SERVER_OVERLOAD','SERVER_UNAVAILABLE','HIGH_ERROR_RATE','BANDWIDTH_REDUCTION')),
    device_id uuid REFERENCES public.devices ON DELETE RESTRICT ON UPDATE RESTRICT,
    link_id uuid REFERENCES public.links ON DELETE RESTRICT ON UPDATE RESTRICT,
    service_id uuid REFERENCES public.services ON DELETE RESTRICT ON UPDATE RESTRICT,
    severity text CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    parameters jsonb,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    status text NOT NULL CHECK (status IN ('SCHEDULED','ACTIVE','COMPLETED','CANCELLED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(device_id, link_id, service_id) >= 1),
    CHECK (ended_at >= started_at),
    CHECK (status <> 'COMPLETED' OR ended_at IS NOT NULL)
);

CREATE TABLE public.topology_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_time timestamptz NOT NULL,
    topology_data jsonb NOT NULL CHECK (jsonb_typeof(topology_data) = 'object'),
    reason text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Resource/timestamp indexes support latest observations and historical ranges.
CREATE INDEX links_source_idx ON public.links (source_device_id);
CREATE INDEX links_destination_idx ON public.links (destination_device_id);
CREATE INDEX device_services_service_idx ON public.device_services (service_id);
CREATE INDEX metrics_device_time_idx ON public.metrics (device_id, timestamp DESC);
CREATE INDEX metrics_link_time_idx ON public.metrics (link_id, timestamp DESC);
CREATE INDEX metrics_type_time_idx ON public.metrics (metric_type, timestamp DESC);
CREATE INDEX metrics_time_idx ON public.metrics (timestamp DESC);
CREATE INDEX logs_device_time_idx ON public.logs (device_id, timestamp DESC);
CREATE INDEX logs_service_time_idx ON public.logs (service_id, timestamp DESC);
CREATE INDEX logs_severity_time_idx ON public.logs (severity, timestamp DESC);
CREATE INDEX logs_time_idx ON public.logs (timestamp DESC);
CREATE INDEX events_device_time_idx ON public.events (device_id, timestamp DESC);
CREATE INDEX events_link_time_idx ON public.events (link_id, timestamp DESC);
CREATE INDEX events_service_time_idx ON public.events (service_id, timestamp DESC);
CREATE INDEX events_type_time_idx ON public.events (event_type, timestamp DESC);
CREATE INDEX events_severity_time_idx ON public.events (severity, timestamp DESC);
CREATE INDEX events_time_idx ON public.events (timestamp DESC);
CREATE INDEX anomalies_device_time_idx ON public.anomalies (device_id, detected_at DESC);
CREATE INDEX anomalies_flag_time_idx ON public.anomalies (is_anomaly, detected_at DESC);
CREATE INDEX anomalies_metric_idx ON public.anomalies (metric_id);
CREATE INDEX anomalies_event_idx ON public.anomalies (event_id);
CREATE INDEX incidents_status_severity_idx ON public.incidents (status, severity);
CREATE INDEX incidents_start_idx ON public.incidents (start_time DESC);
CREATE INDEX incident_events_event_idx ON public.incident_events (event_id);
CREATE INDEX root_causes_device_idx ON public.root_causes (device_id);
CREATE INDEX root_causes_link_idx ON public.root_causes (link_id);
CREATE INDEX root_causes_service_idx ON public.root_causes (service_id);
CREATE INDEX evidence_source_idx ON public.root_cause_evidence (source_type, source_id);
CREATE INDEX impact_incident_idx ON public.impact_records (incident_id);
CREATE INDEX impact_device_idx ON public.impact_records (device_id);
CREATE INDEX impact_link_idx ON public.impact_records (link_id);
CREATE INDEX impact_service_idx ON public.impact_records (service_id);
CREATE INDEX recommendations_incident_cause_idx ON public.recommendations (incident_id, root_cause_id);
CREATE INDEX ai_analyses_incident_time_idx ON public.ai_analyses (incident_id, created_at DESC);
CREATE INDEX faults_device_time_idx ON public.fault_injections (device_id, started_at DESC);
CREATE INDEX faults_link_time_idx ON public.fault_injections (link_id, started_at DESC);
CREATE INDEX faults_service_time_idx ON public.fault_injections (service_id, started_at DESC);
CREATE INDEX faults_time_idx ON public.fault_injections (started_at DESC);
CREATE INDEX snapshots_time_idx ON public.topology_snapshots (snapshot_time DESC);

-- Internal trigger function has no caller privileges or user-controlled search path.
CREATE FUNCTION public.netrca_touch_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.netrca_touch_updated_at() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER devices_updated_at BEFORE UPDATE ON public.devices FOR EACH ROW EXECUTE FUNCTION public.netrca_touch_updated_at();
CREATE TRIGGER links_updated_at BEFORE UPDATE ON public.links FOR EACH ROW EXECUTE FUNCTION public.netrca_touch_updated_at();
CREATE TRIGGER services_updated_at BEFORE UPDATE ON public.services FOR EACH ROW EXECUTE FUNCTION public.netrca_touch_updated_at();
CREATE TRIGGER incidents_updated_at BEFORE UPDATE ON public.incidents FOR EACH ROW EXECUTE FUNCTION public.netrca_touch_updated_at();

-- No application identity/role model exists yet. Deny clients by both ACL and RLS.
-- Only the explicitly named NetRCA tables are affected, never unrelated public tables.
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'devices','links','services','device_services','metrics','logs','events',
        'anomalies','incidents','incident_events','root_causes','root_cause_evidence',
        'impact_records','recommendations','ai_analyses','fault_injections','topology_snapshots'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', table_name);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO service_role', table_name);
    END LOOP;
END;
$$;
