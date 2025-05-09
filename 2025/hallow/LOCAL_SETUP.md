# Setting Up Netflix Hollow Locally

This guide explains how to set up Netflix Hollow locally for development and testing purposes.

## What is Netflix Hollow?

[Netflix Hollow](https://hollow.how/) is a Java library and toolset for managing in-memory datasets. It's particularly useful for high-performance, read-heavy applications that need to manage large datasets efficiently.

## Local Installation Steps

### Prerequisites

- Java 11 or higher
- Maven
- Git
- Python 3 with virtual environment support (`python3-venv` and `python3-full` packages)

### Step 1: Install Dependencies

Run the installation script which checks for prerequisites and installs the necessary Python dependencies:

```bash
./install_deps.sh
```

When prompted, answer "y" to install Netflix Hollow locally. This will:

1. Clone the Hollow repository from GitHub
2. Build Hollow using Maven
3. Create a simple Hollow producer application
4. Set up the necessary directory structure

### Step 2: Set Up the Consumer

After installing the basic dependencies, set up the Hollow consumer:

```bash
./setup_consumer.sh
```

This will:
1. Create a simple Hollow consumer application
2. Build the consumer using Maven
3. Set up scripts to run the consumer

### Step 3: Activate the Virtual Environment

Before using any Python scripts, you need to activate the virtual environment:

```bash
# From the hallow directory
source ./activate_env.sh
```

This will activate the Python virtual environment with all required dependencies.

### Step 4: Publish Data to Hollow

To publish your eBPF metrics data to the local Hollow store:

```bash
# First, activate the virtual environment
source ./activate_env.sh

# Convert your eBPF metrics to JSON
./ebpf_to_json.py metrics_file.txt -o metrics.json --pretty

# Convert to Hollow format
./ebpf_to_hollow.py metrics.json --local --output hollow_metrics.json

# Then, run the local producer to publish the data
./hollow-local/run_producer.sh hollow_metrics.json
```

### Step 5: Consume Data from Hollow

To consume the data you've published:

```bash
./hollow-local/run_consumer.sh
```

The consumer will read the data from the local Hollow store and display basic information about it.

## How It Works

### Local Hollow Architecture

The local Hollow setup consists of:

1. **Producer**: Writes data to the filesystem in Hollow format
2. **Consumer**: Reads data from the filesystem
3. **Publish Directory**: Where the Hollow blobs (snapshots and deltas) are stored

```
hollow-local/
├── repo/           # Cloned Hollow repository
├── producer/       # Simple producer application
├── consumer/       # Simple consumer application
├── publish/        # Where Hollow data is published
├── run_producer.sh # Script to run the producer
└── run_consumer.sh # Script to run the consumer
```

### Data Flow

1. Your eBPF metrics are converted to JSON using `ebpf_to_json.py`
2. The local Hollow producer reads this JSON and publishes Hollow blobs
3. The local Hollow consumer reads these blobs and initializes its state
4. The consumer periodically checks for updates (every 10 seconds)

## Common Issues

### Java Version

Hollow requires Java 11 or higher. If you encounter errors, check your Java version:

```bash
java -version
```

### Maven Build Failures

If the Maven build fails, it might be due to network issues or missing dependencies. Try running the build again:

```bash
cd hollow-local/producer && mvn clean package
cd hollow-local/consumer && mvn clean package
```

### No Data Available

If the consumer reports "No data available", ensure you've run the producer first and check the contents of the `hollow-local/publish` directory.

## Next Steps

After setting up Hollow locally, you can:

1. Modify the producer to better handle your eBPF metrics data structure
2. Create a schema for your specific metrics types
3. Generate a proper Hollow API for your data model using the Hollow code generator
4. Build more sophisticated visualizations or integrations using the Hollow data

For more information, refer to the [Hollow documentation](https://hollow.how/) or the [GitHub repository](https://github.com/Netflix/hollow).
