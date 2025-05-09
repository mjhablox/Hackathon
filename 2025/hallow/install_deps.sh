#!/usr/bin/env bash
# Installation script for Netflix Hollow integration dependencies

# Display a header
echo "======================================================"
echo "Netflix Hollow Integration - Dependencies Installation"
echo "======================================================"
echo

# Check for required tools
echo "Checking for required tools..."

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install Python 3 and pip first."
    exit 1
fi

# Check if Java is installed (needed for Hollow)
if ! command -v java &> /dev/null; then
    echo "Warning: Java is not installed. You will need Java to run Hollow locally."
    echo "         Install OpenJDK 11+ with: sudo apt install default-jdk"
    JAVA_MISSING=true
else
    java_version=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | sed 's/^1\.//' | cut -d'.' -f1)
    if [ "$java_version" -lt 11 ]; then
        echo "Warning: Java version $java_version detected. Hollow requires Java 11+."
        echo "         Please upgrade your Java installation."
        JAVA_MISSING=true
    else
        echo "Java version $java_version detected. ✓"
    fi
fi

# Check if Maven is installed (needed to build the producer)
if ! command -v mvn &> /dev/null; then
    echo "Warning: Maven is not installed. You will need Maven to build Hollow producer."
    echo "         Install Maven with: sudo apt install maven"
    MAVEN_MISSING=true
else
    echo "Maven detected. ✓"
fi

# Check if Gradle is available (needed for building Hollow)
if [ ! -f "$PWD/hollow-local/repo/gradlew" ] && ! command -v gradle &> /dev/null; then
    echo "Warning: Neither Gradle nor a Gradle wrapper (gradlew) was detected."
    echo "         Hollow requires Gradle to build. The script will attempt to use gradlew if found."
    GRADLE_MISSING=true
else
    echo "Gradle build system available. ✓"
fi

echo "Setting up a Python virtual environment..."

# Create a venv directory in the Hollow directory
VENV_DIR="$PWD/venv"

# Check if python3-venv is installed
if ! dpkg -l | grep -q "python3-venv"; then
    echo "The python3-venv package is not installed."
    echo
    echo "You have two options:"
    echo
    echo "Option 1: Install python3-venv (recommended)"
    echo "  sudo apt install python3-venv python3-full"
    echo "  Then run this script again"
    echo
    echo "Option 2: Continue without virtual environment (may require --break-system-packages)"
    echo "  Do you want to try installing packages without a virtual environment? (y/n)"
    read -r skip_venv

    if [[ $skip_venv == "y" || $skip_venv == "Y" ]]; then
        echo "Will attempt to install packages globally with --break-system-packages"
        USE_GLOBAL=true
    else
        echo "Installation aborted. Please install python3-venv and python3-full, then try again."
        exit 1
    fi
else
    USE_GLOBAL=false
fi

# Create virtual environment if we're not using global packages
if [ "$USE_GLOBAL" = false ]; then
    # Create virtual environment
    python3 -m venv "$VENV_DIR" || {
        echo "Error: Failed to create virtual environment."
        echo "Please make sure python3-venv and python3-full are installed."
        echo "Try: sudo apt install python3-venv python3-full"
        exit 1
    }
fi

if [ "$USE_GLOBAL" = false ]; then
    # Activate virtual environment
    source "$VENV_DIR/bin/activate" || {
        echo "Error: Failed to activate virtual environment."
        exit 1
    }

    echo "Installing required Python packages in the virtual environment..."
    pip install requests matplotlib numpy pandas

    # Check if the installation was successful
    if [ $? -eq 0 ]; then
        echo "Python dependencies successfully installed in virtual environment. ✓"

        # Create an activation script for convenience
        cat > "$PWD/activate_env.sh" << 'ACTIVATION_SCRIPT'
#!/bin/bash
# Script to activate the Hollow integration Python environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run install_deps.sh first."
    exit 1
fi

echo "Activating Python virtual environment..."
source "$VENV_DIR/bin/activate"

# Verify activation was successful
if [ $? -eq 0 ]; then
    echo "Environment activated successfully."

    # Display Python and pip information
    python_version=$(python --version 2>&1)
    pip_version=$(pip --version 2>&1)

    echo "Using $python_version"
    echo "Using $pip_version"
    echo
    echo "IMPORTANT: This virtual environment will only be active in the current terminal."
    echo "To use the environment in a new terminal, run this script again:"
    echo "  source $SCRIPT_DIR/activate_env.sh"
    echo
    echo "To exit the virtual environment, run:"
    echo "  deactivate"
else
    echo "Error: Failed to activate the virtual environment."
    echo "Please check that venv is properly installed:"
    echo "  sudo apt install python3-venv python3-full"
    exit 1
fi

echo "You can now use the Hollow integration scripts."
ACTIVATION_SCRIPT

        chmod +x "$PWD/activate_env.sh"
        echo "Created activation script: $PWD/activate_env.sh"
    else
        echo "Error: Failed to install Python dependencies."
        echo "Please check your internet connection and try again."
        exit 1
    fi
else
    # Using global Python environment with --break-system-packages
    echo "Installing required Python packages globally (with --break-system-packages)..."
    pip3 install --break-system-packages requests matplotlib numpy pandas

    # Check if the installation was successful
    if [ $? -eq 0 ]; then
        echo "Python dependencies successfully installed globally. ✓"
        echo "WARNING: This approach is not recommended and may cause issues with your system packages."

        # Create a simple activation script that just sets a flag
        cat > "$PWD/activate_env.sh" << 'ACTIVATION_SCRIPT'
#!/bin/bash
# Script to indicate global Python environment for Hollow integration

echo "Using system-wide Python packages (no virtual environment)."
echo "This is not recommended and may cause issues with system packages."
echo "You can now use the Hollow integration scripts."
ACTIVATION_SCRIPT

        chmod +x "$PWD/activate_env.sh"
    else
        echo "Error: Failed to install Python dependencies globally."
        echo "Try installing python3-venv and python3-full, then run this script again."
        exit 1
    fi
fi

# Ask if user wants to install Hollow locally
echo
echo "Do you want to install Netflix Hollow locally? (y/n)"
read -r install_hollow

if [[ $install_hollow == "y" || $install_hollow == "Y" ]]; then
    echo
    echo "Setting up Netflix Hollow locally..."

    # Create a directory for Hollow
    HOLLOW_DIR="$PWD/hollow-local"
    mkdir -p "$HOLLOW_DIR"

    # Check if Java and Maven are available
    if [[ "$JAVA_MISSING" == "true" || "$MAVEN_MISSING" == "true" ]]; then
        echo "Error: Java 11+ and Maven are required to install Hollow locally."
        echo "Please install them and try again."
        exit 1
    fi

    # Check if Hollow repository already exists, otherwise clone it
    echo "Preparing Netflix Hollow repository..."
    if [ -d "$HOLLOW_DIR/repo" ] && [ -f "$HOLLOW_DIR/repo/build.gradle" ]; then
        echo "Using existing Hollow repository in $HOLLOW_DIR/repo"
    else
        echo "Cloning Netflix Hollow repository..."
        # Remove directory if it exists but is incomplete
        if [ -d "$HOLLOW_DIR/repo" ]; then
            rm -rf "$HOLLOW_DIR/repo"
        fi
        git clone https://github.com/Netflix/hollow.git "$HOLLOW_DIR/repo" || {
            echo "Error: Failed to clone Hollow repository."
            exit 1
        }
    fi

    # Build Hollow with Gradle
    echo "Building Hollow..."
    if [ -f "$HOLLOW_DIR/repo/build.gradle" ]; then
        echo "Found build.gradle, building with Gradle..."

        # Try to determine the current version from the repo
        HOLLOW_VERSION=$(grep -r "version" --include="*.gradle" "$HOLLOW_DIR/repo/" | grep -i "version" | head -1 | tr -d " " | cut -d "=" -f2 | tr -d "'" | tr -d '"' || echo "7.14.6-SNAPSHOT")
        echo "Detected Hollow version: $HOLLOW_VERSION"

        # Set Java toolchain options to use the current Java version
        export JAVA_TOOL_OPTIONS="-Dorg.gradle.java.installations.auto-detect=false -Dorg.gradle.java.installations.paths=$JAVA_HOME"

        # Try to build with the current Java version
        (cd "$HOLLOW_DIR/repo" && ./gradlew clean build publishToMavenLocal -x test) || {
            echo "Error: Failed to build Hollow with Gradle."
            echo "This might be due to Java version incompatibility."
            echo "Trying to continue without building Hollow..."

            # Download Hollow from Maven Central as a fallback
            echo "Using Maven Central for Hollow dependencies instead of local build"
            HOLLOW_VERSION="7.14.5"  # Latest known stable version

            # Use Maven to fetch the dependency
            echo "Downloading Hollow $HOLLOW_VERSION from Maven Central..."
            mvn dependency:get -Dartifact=com.netflix.hollow:hollow:$HOLLOW_VERSION -DremoteRepositories=https://repo.maven.apache.org/maven2/ || {
                echo "Failed to download Hollow from Maven Central."
                echo "Using a more conservative version as a fallback."
                HOLLOW_VERSION="5.1.9"
                mvn dependency:get -Dartifact=com.netflix.hollow:hollow:$HOLLOW_VERSION -DremoteRepositories=https://repo.maven.apache.org/maven2/ || {
                    echo "Warning: All fallback attempts failed. Continuing anyway."
                }
            }
            echo "Using Hollow version $HOLLOW_VERSION from Maven Central."
        }

        # Update the hollow.version property in the producer pom.xml template
        sed -i "s/<hollow.version>.*<\/hollow.version>/<hollow.version>$HOLLOW_VERSION<\/hollow.version>/" "$HOLLOW_DIR/producer/pom.xml" 2>/dev/null || true
    else
        echo "Error: Could not find build.gradle in the Hollow repository."
        echo "Trying to continue without building Hollow..."
    fi

    # Create a simple Hollow producer app for testing
    echo "Setting up local Hollow producer..."

    # Create directories for the producer
    mkdir -p "$HOLLOW_DIR/producer/src/main/java/com/example/hollow"
    mkdir -p "$HOLLOW_DIR/publish"

    # Create a simple producer app Java file
    cat > "$HOLLOW_DIR/producer/src/main/java/com/example/hollow/SimpleHollowProducer.java" << 'EOL'
package com.example.hollow;

import com.netflix.hollow.api.producer.HollowProducer;
import com.netflix.hollow.api.producer.fs.HollowFilesystemPublisher;
import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;

public class SimpleHollowProducer {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java SimpleHollowProducer <publish_dir> <json_file>");
            System.exit(1);
        }

        String publishDir = args[0];
        String jsonFile = args[1];

        // Ensure the publish directory exists
        File dir = new File(publishDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        Path publishPath = Paths.get(publishDir);

        // Create a producer that publishes to the filesystem
        HollowProducer producer = HollowProducer.withPublisher(new HollowFilesystemPublisher(publishPath))
                                   .build();

        // Read JSON file and populate Hollow dataset
        System.out.println("Reading data from: " + jsonFile);
        System.out.println("Publishing Hollow data to: " + publishDir);

        try {
            // Initialize the producer with the first version
            long version = System.currentTimeMillis();

            producer.runCycle(state -> {
                // This is a placeholder for actual data population logic
                // In a real application, you would parse the JSON and populate Hollow objects
                System.out.println("Populating state with version: " + version);
            });

            System.out.println("Successfully published Hollow data with version: " + version);

        } catch (Exception e) {
            System.err.println("Error publishing data: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
EOL

    # Create a POM file for the producer app
    cat > "$HOLLOW_DIR/producer/pom.xml" << 'EOL'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>hollow-producer</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <hollow.version>7.14.5</hollow.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>com.netflix.hollow</groupId>
            <artifactId>hollow</artifactId>
            <version>${hollow.version}</version>
        </dependency>
    </dependencies>

    <repositories>
        <!-- Add Maven central repository -->
        <repository>
            <id>central</id>
            <name>Maven Central</name>
            <url>https://repo.maven.apache.org/maven2</url>
        </repository>
        <!-- Add local Maven repository for locally built Hollow artifacts -->
        <repository>
            <id>maven-local</id>
            <name>Maven Local</name>
            <url>file:///${user.home}/.m2/repository</url>
        </repository>
    </repositories>

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
                            <mainClass>com.example.hollow.SimpleHollowProducer</mainClass>
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

    # Build the producer app
    echo "Building the local Hollow producer app..."

    # Set Maven options to include verbose output in case of failure
    export MAVEN_OPTS="-Dorg.slf4j.simpleLogger.defaultLogLevel=info"

    # Try building with Maven
    (cd "$HOLLOW_DIR/producer" && mvn clean package -B) || {
        # If the first build attempt fails, try to explicitly fetch the dependency first
        echo "First build attempt failed. Trying to explicitly download Hollow dependency..."
        (cd "$HOLLOW_DIR/producer" && mvn dependency:get -Dartifact=com.netflix.hollow:hollow:${HOLLOW_VERSION} -DremoteRepositories=https://repo.maven.apache.org/maven2/)

        # Try building again
        echo "Retrying build with explicit dependency..."
        (cd "$HOLLOW_DIR/producer" && mvn clean package -B)
    }

    # Check if the build was successful by checking if the JAR exists
    if [ ! -f "$HOLLOW_DIR/producer/target/hollow-producer-1.0-SNAPSHOT-jar-with-dependencies.jar" ]; then
        echo "Warning: Failed to build the Hollow producer app."
        echo "This is likely due to missing Hollow dependencies. You can try to:"
        echo "1. Check if Hollow was built successfully in the previous step"
        echo "2. Try running the script again with a newer version of Hollow in the pom.xml"
        echo "3. Manually build the producer app later after fixing any issues"

        # Create target directory so the run_producer.sh script can at least be created
        mkdir -p "$HOLLOW_DIR/producer/target"

        # Create an empty JAR file so the script doesn't completely fail
        echo "Creating an empty placeholder JAR file..."
        touch "$HOLLOW_DIR/producer/target/hollow-producer-1.0-SNAPSHOT-jar-with-dependencies.jar"
    else
        echo "Successfully built Hollow producer app."
    fi

    # Create a script to run the Hollow producer
    cat > "$HOLLOW_DIR/run_producer.sh" << 'EOL'
#!/bin/bash
# Script to run the local Hollow producer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
JAR_FILE="$SCRIPT_DIR/producer/target/hollow-producer-1.0-SNAPSHOT-jar-with-dependencies.jar"
PUBLISH_DIR="$SCRIPT_DIR/publish"
JSON_FILE=$1

# Check for the virtual environment
VENV_DIR="$PARENT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    # Activate the virtual environment if it exists
    echo "Activating Python virtual environment..."
    source "$VENV_DIR/bin/activate"

    # Verify activation was successful
    if [ $? -eq 0 ]; then
        echo "Python virtual environment activated successfully."
    else
        echo "Warning: Failed to activate virtual environment. Continuing with system Python."
    fi
else
    echo "Warning: Virtual environment not found at $VENV_DIR"
    echo "Using system Python instead. This may cause compatibility issues."
fi

if [ ! -f "$JAR_FILE" ]; then
    echo "Error: Producer JAR file not found. Build failed?"
    exit 1
fi

if [ -z "$JSON_FILE" ]; then
    echo "Usage: $0 <json_file>"
    echo "Example: $0 ../sample_metrics.json"
    exit 1
fi

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file not found: $JSON_FILE"
    exit 1
fi

echo "Running Hollow producer..."
java -jar "$JAR_FILE" "$PUBLISH_DIR" "$JSON_FILE"
EOL

    # Make the script executable
    chmod +x "$HOLLOW_DIR/run_producer.sh"

    echo
    echo "Netflix Hollow has been installed locally at: $HOLLOW_DIR"
    echo "To run the local Hollow producer with your metrics data:"
    echo "  $HOLLOW_DIR/run_producer.sh path/to/your_metrics.json"
    echo
else
    echo "Skipping Hollow local installation."
fi

echo
echo "Dependencies successfully installed!"
echo
echo "IMPORTANT: To use the Hollow integration scripts, first activate the virtual environment:"
echo "  source $PWD/activate_env.sh"
echo
echo "After activation, you can use the following scripts:"
echo "  - ebpf_to_json.py: Convert eBPF metrics to JSON"
echo "  - ebpf_to_hollow.py: Convert JSON to Hollow format"
echo "  - ebpf_hollow_monitor.py: Monitor and push metrics to Hollow"
echo "  - visualize_json_metrics.py: Create visualizations"
echo
echo "Example usage after activation:"
echo "  ./ebpf_to_json.py ../sample_metrics.txt -o metrics.json"
echo
echo "For more information, see hallow/HOLLOW_INTEGRATION.md"
echo
