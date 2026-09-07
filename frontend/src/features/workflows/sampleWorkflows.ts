/**
 * Infralytix — Sample Workflow Templates.
 *
 * Pre-defined valid workflow DAGs for quick exploration and testing.
 */

export const SAMPLE_WORKFLOWS: Record<
  string,
  { name: string; description: string; json: string }
> = {
  diamond_dag: {
    name: 'Diamond DAG (ETL Pipeline)',
    description: 'Classic diamond structure: Ingestion fork into Clean & Transform, joined in Aggregation.',
    json: JSON.stringify(
      {
        tasks: [
          {
            id: 'extract_data',
            name: 'Data Ingestion',
            category: 'io_bound',
            baseline_time_seconds: 120,
            baseline_vcpu: 2,
            baseline_ram_gb: 4,
            depends_on: [],
          },
          {
            id: 'clean_features',
            name: 'Feature Cleaning',
            category: 'cpu_bound',
            baseline_time_seconds: 300,
            baseline_vcpu: 4,
            baseline_ram_gb: 8,
            depends_on: ['extract_data'],
          },
          {
            id: 'embed_vectors',
            name: 'Vector Embedding',
            category: 'memory_bound',
            baseline_time_seconds: 240,
            baseline_vcpu: 4,
            baseline_ram_gb: 16,
            depends_on: ['extract_data'],
          },
          {
            id: 'aggregate_index',
            name: 'Search Index Aggregation',
            category: 'io_bound',
            baseline_time_seconds: 180,
            baseline_vcpu: 2,
            baseline_ram_gb: 8,
            depends_on: ['clean_features', 'embed_vectors'],
          },
        ],
      },
      null,
      2
    ),
  },
  deep_learning: {
    name: 'Deep Learning & Evaluation',
    description: 'Pipeline with data preparation, parallel hyperparam tuning, and GPU model training.',
    json: JSON.stringify(
      {
        tasks: [
          {
            id: 'dataset_prep',
            name: 'Dataset Tokenization',
            category: 'cpu_bound',
            baseline_time_seconds: 180,
            baseline_vcpu: 4,
            baseline_ram_gb: 16,
            depends_on: [],
          },
          {
            id: 'train_model',
            name: 'Transformer Fine-tuning',
            category: 'gpu_bound',
            baseline_time_seconds: 900,
            baseline_vcpu: 8,
            baseline_ram_gb: 32,
            depends_on: ['dataset_prep'],
          },
          {
            id: 'quantize_model',
            name: 'Model Quantization (FP16/INT8)',
            category: 'memory_bound',
            baseline_time_seconds: 150,
            baseline_vcpu: 4,
            baseline_ram_gb: 16,
            depends_on: ['train_model'],
          },
          {
            id: 'eval_benchmark',
            name: 'Accuracy & Latency Benchmark',
            category: 'cpu_bound',
            baseline_time_seconds: 200,
            baseline_vcpu: 4,
            baseline_ram_gb: 8,
            depends_on: ['quantize_model'],
          },
        ],
      },
      null,
      2
    ),
  },
  parallel_analytics: {
    name: 'Parallel Batch Analytics',
    description: 'High-throughput fan-out across regions followed by summary reduce.',
    json: JSON.stringify(
      {
        tasks: [
          {
            id: 'partition_source',
            name: 'Partition Shards',
            category: 'io_bound',
            baseline_time_seconds: 60,
            baseline_vcpu: 2,
            baseline_ram_gb: 4,
            depends_on: [],
          },
          {
            id: 'process_shard_1',
            name: 'Analyze Shard #1',
            category: 'cpu_bound',
            baseline_time_seconds: 250,
            baseline_vcpu: 4,
            baseline_ram_gb: 8,
            depends_on: ['partition_source'],
          },
          {
            id: 'process_shard_2',
            name: 'Analyze Shard #2',
            category: 'cpu_bound',
            baseline_time_seconds: 280,
            baseline_vcpu: 4,
            baseline_ram_gb: 8,
            depends_on: ['partition_source'],
          },
          {
            id: 'process_shard_3',
            name: 'Analyze Shard #3',
            category: 'cpu_bound',
            baseline_time_seconds: 220,
            baseline_vcpu: 4,
            baseline_ram_gb: 8,
            depends_on: ['partition_source'],
          },
          {
            id: 'generate_report',
            name: 'Compile Synthesis Report',
            category: 'io_bound',
            baseline_time_seconds: 90,
            baseline_vcpu: 2,
            baseline_ram_gb: 4,
            depends_on: ['process_shard_1', 'process_shard_2', 'process_shard_3'],
          },
        ],
      },
      null,
      2
    ),
  },
}
