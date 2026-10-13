-- Phase 6: store directly observed interface state and cumulative counters.
ALTER TABLE public.metrics DROP CONSTRAINT metrics_metric_type_check;
ALTER TABLE public.metrics ADD CONSTRAINT metrics_metric_type_check CHECK (
    metric_type IN ('LATENCY','PACKET_LOSS','BANDWIDTH','THROUGHPUT','CPU','MEMORY',
                    'ERROR_RATE','AVAILABILITY','INTERFACE_STATE','RX_BYTES','TX_BYTES',
                    'RX_PACKETS','TX_PACKETS','RX_ERRORS','TX_ERRORS')
);

-- Repeating the same observation must not create another evidence row.
CREATE UNIQUE INDEX metrics_observation_key_idx ON public.metrics ((metadata->>'observation_key'))
    WHERE metadata ? 'observation_key';
CREATE UNIQUE INDEX logs_observation_key_idx ON public.logs ((metadata->>'observation_key'))
    WHERE metadata ? 'observation_key';
CREATE UNIQUE INDEX events_active_dedup_key_idx ON public.events ((metadata->>'dedup_key'))
    WHERE status = 'DETECTED' AND metadata ? 'dedup_key';
