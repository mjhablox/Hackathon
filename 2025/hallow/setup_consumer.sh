#!/usr/bin/env bash
# Script to set up a local Hollow consumer for testing

# Display a header
echo "======================================================"
echo "Netflix Hollow - Local Consumer Setup"
echo "======================================================"
echo

# Check if Java and Maven are installed
if ! command -v java &> /dev/null; then
    echo "Error: Java is not installed. Please install Java 11+ first."
    exit 1
fi

if ! command -v mvn &> /dev/null; then
    echo "Error: Maven is not installed. Please install Maven first."
    exit 1
fi

# Create the directory for the consumer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOLLOW_DIR="$SCRIPT_DIR/hollow-local"

if [ ! -d "$HOLLOW_DIR" ]; then
    echo "Error: Hollow local directory not found at $HOLLOW_DIR"
    echo "Please run install_deps.sh first to set up Hollow locally."
    exit 1
fi

CONSUMER_DIR="$HOLLOW_DIR/consumer"
mkdir -p "$CONSUMER_DIR/src/main/java/com/example/hollow"

# Create the consumer app Java file
cat > "$CONSUMER_DIR/src/main/java/com/example/hollow/SimpleHollowConsumer.java" << 'EOL'
package com.example.hollow;

import com.netflix.hollow.api.consumer.HollowConsumer;
import com.netflix.hollow.api.consumer.fs.HollowFilesystemBlobRetriever;
import com.netflix.hollow.api.metrics.HollowConsumerMetrics;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.TimeUnit;

public class SimpleHollowConsumer {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Usage: java SimpleHollowConsumer <publish_dir>");
            System.exit(1);
        }

        String publishDir = args[0];
        Path publishPath = Paths.get(publishDir);

        System.out.println("Reading Hollow data from: " + publishDir);

        // Create a consumer that reads from the filesystem
        HollowConsumer consumer = HollowConsumer.withBlobRetriever(new HollowFilesystemBlobRetriever(publishPath))
                                 .withRefreshListener(new HollowConsumer.RefreshListener() {
                                     @Override
                                     public void refreshStarted(long currentVersion, long requestedVersion) {
                                         System.out.println("Refresh started: currentVersion=" + currentVersion +
                                                           ", requestedVersion=" + requestedVersion);
                                     }

                                     @Override
                                     public void snapshotUpdateOccurred(HollowConsumer.RefreshListener.Metrics metrics) {
                                         System.out.println("Snapshot complete: " + metrics.getBlobsLoadedMetrics());
                                     }

                                     @Override
                                     public void deltaUpdateOccurred(HollowConsumer.RefreshListener.Metrics metrics) {
                                         System.out.println("Delta update complete: " + metrics.getBlobsLoadedMetrics());
                                     }

                                     @Override
                                     public void refreshSuccessful(long beforeVersion, long afterVersion, long requestedVersion) {
                                         System.out.println("Refresh successful: beforeVersion=" + beforeVersion +
                                                           ", afterVersion=" + afterVersion +
                                                           ", requestedVersion=" + requestedVersion);
                                     }

                                     @Override
                                     public void refreshFailed(long beforeVersion, long requestedVersion, Throwable failureCause) {
                                         System.out.println("Refresh failed: beforeVersion=" + beforeVersion +
                                                           ", requestedVersion=" + requestedVersion);
                                         failureCause.printStackTrace();
                                     }
                                 })
                                 .build();

        try {
            // Initialize the consumer
            consumer.triggerRefresh();

            // Basic consumer metrics
            long version = consumer.getCurrentVersionId();
            if (version != HollowConsumer.NO_VERSION_REQUIRED) {
                System.out.println("Consumer initialized with version: " + version);

                // Here you would typically access your Hollow objects
                // For example, if you had a MetricsState type:
                // MetricsStateAPI api = new MetricsStateAPI(consumer);
                // Collection<MetricsStateHollow> metrics = api.getAllMetricsState();

                // For this example, we'll just report the metrics
                HollowConsumerMetrics metrics = consumer.getMetrics();
                System.out.println("Refresh count: " + metrics.getRefreshCount());

                // Keep running to watch for updates
                System.out.println("Watching for updates. Press Ctrl+C to exit.");
                while (true) {
                    consumer.triggerRefresh();
                    TimeUnit.SECONDS.sleep(10);
                }
            } else {
                System.out.println("No data available in the Hollow store.");
            }
        } catch (Exception e) {
            System.err.println("Error consuming data: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
EOL

# Create a POM file for the consumer app
cat > "$CONSUMER_DIR/pom.xml" << 'EOL'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>hollow-consumer</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <hollow.version>5.1.9</hollow.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>com.netflix.hollow</groupId>
            <artifactId>hollow</artifactId>
            <version>${hollow.version}</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-assembly-plugin</artifactId>
                <version>3.3.0</version>
                <configuration>
                    <descriptorRefs>
                        <descriptorRef>jar-with-dependencies</descriptorRef>
                    </descriptorRefs>
                    <archive>
                        <manifest>
                            <mainClass>com.example.hollow.SimpleHollowConsumer</mainClass>
                        </manifest>
                    </archive>
                </configuration>
                <executions>
                    <execution>
                        <id>make-assembly</id>
                        <phase>package</phase>
                        <goals>
                            <goal>single</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
EOL

# Build the consumer app
echo "Building the local Hollow consumer app..."
(cd "$CONSUMER_DIR" && mvn clean package) || {
    echo "Error: Failed to build the Hollow consumer app."
    exit 1
}

# Create a script to run the Hollow consumer
cat > "$HOLLOW_DIR/run_consumer.sh" << 'EOL'
#!/bin/bash
# Script to run the local Hollow consumer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR_FILE="$SCRIPT_DIR/consumer/target/hollow-consumer-1.0-SNAPSHOT-jar-with-dependencies.jar"
PUBLISH_DIR="$SCRIPT_DIR/publish"

if [ ! -f "$JAR_FILE" ]; then
    echo "Error: Consumer JAR file not found. Build failed?"
    exit 1
fi

echo "Running Hollow consumer..."
java -jar "$JAR_FILE" "$PUBLISH_DIR"
EOL

# Make the script executable
chmod +x "$HOLLOW_DIR/run_consumer.sh"

echo
echo "Local Hollow consumer has been set up successfully!"
echo "To run the Hollow consumer and read data from the local producer:"
echo "  $HOLLOW_DIR/run_consumer.sh"
echo
echo "Note: Make sure to first publish data with the producer before running the consumer."
echo "You can publish sample data with:"
echo "  $HOLLOW_DIR/run_producer.sh ../sample_metrics.json"
echo
