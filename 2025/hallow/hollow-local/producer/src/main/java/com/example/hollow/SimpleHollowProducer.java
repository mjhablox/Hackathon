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
