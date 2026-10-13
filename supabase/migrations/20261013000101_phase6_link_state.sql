-- A link state is measured from the two Phase 5 endpoint interfaces.
ALTER TABLE public.metrics DROP CONSTRAINT metrics_metric_type_check;
ALTER TABLE public.metrics ADD CONSTRAINT metrics_metric_type_check CHECK (
    metric_type IN ('LATENCY','PACKET_LOSS','BANDWIDTH','THROUGHPUT','CPU','MEMORY',
                    'ERROR_RATE','AVAILABILITY','INTERFACE_STATE','LINK_STATE','RX_BYTES','TX_BYTES',
                    'RX_PACKETS','TX_PACKETS','RX_ERRORS','TX_ERRORS')
);
