
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Test file with intentional security, performance, code quality,
 * best practice, and maintainability issues.
 * 
 * MAINTAINABILITY ISSUE: Class does too many things (God Object)
 */
public class VulnerableDataProcessor {
    
    // SECURITY ISSUE: Hardcoded credentials
    private static final String DB_PASSWORD = "admin123";
    private static final String API_KEY = "sk-1234567890abcdef";
    private static final String ADMIN_USER = "admin";
    private static final String ADMIN_PASS = "password123";
    
    // BEST PRACTICES ISSUE: Mutable static field
    public static List<User> userCache = new ArrayList<>();
    
    // PERFORMANCE ISSUE: No connection pooling
    private Connection connection;
    
    // BEST PRACTICES ISSUE: Missing initialization
    private UserValidator validator;
    
    /**
     * SECURITY ISSUE: SQL Injection vulnerability
     * BEST PRACTICES ISSUE: No resource management (not using try-with-resources)
     * PERFORMANCE ISSUE: Creating new connection every call
     */
    public User queryUserById(String userId) {
        try {
            // SECURITY: No parameterized query
            String query = "SELECT * FROM users WHERE id = " + userId;
            
            Connection conn = DriverManager.getConnection(
                "jdbc:mysql://localhost:3306/admin",
                "root",
                DB_PASSWORD
            );
            
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(query);
            
            User user = null;
            if (rs.next()) {
                user = new User(
                    rs.getString("id"),
                    rs.getString("name"),
                    rs.getString("email")
                );
            }
            
            // BEST PRACTICES ISSUE: Not closing resources
            rs.close();
            stmt.close();
            conn.close();
            
            return user;
            
        } catch (SQLException e) {
            // CODE QUALITY ISSUE: Swallowing exception
            e.printStackTrace();
            return null;
        }
    }
    
    /**
     * PERFORMANCE ISSUE: O(n²) algorithm with nested loops
     * CODE QUALITY ISSUE: No input validation
     * MAINTAINABILITY ISSUE: Magic numbers and unclear logic
     */
    public List<User> findDuplicateUsers(List<User> users) {
        List<User> duplicates = new ArrayList<>();
        
        for (int i = 0; i < users.size(); i++) {
            for (int j = i + 1; j < users.size(); j++) {
                // MAINTAINABILITY ISSUE: Unclear comparison logic
                if (users.get(i).equals(users.get(j))) {
                    duplicates.add(users.get(i));
                    duplicates.add(users.get(j));
                }
            }
        }
        
        return duplicates;
    }
    
    /**
     * SECURITY ISSUE: Unsafe deserialization
     * CODE QUALITY ISSUE: No error handling
     */
    public Object deserializeUserData(byte[] data) throws Exception {
        ByteArrayInputStream bais = new ByteArrayInputStream(data);
        ObjectInputStream ois = new ObjectInputStream(bais);
        
        // SECURITY: Deserialization attack vulnerability
        Object obj = ois.readObject();
        
        // BEST PRACTICES ISSUE: Not closing stream
        return obj;
    }
    
    /**
     * PERFORMANCE ISSUE: Loading entire file into memory
     * CODE QUALITY ISSUE: Inadequate exception handling
     * BEST PRACTICES ISSUE: No null checks
     */
    public void processLargeFile(String filePath) {
        try {
            File file = new File(filePath);
            byte[] fileContent = new byte[(int) file.length()];
            
            FileInputStream fis = new FileInputStream(file);
            fis.read(fileContent);
            
            // BEST PRACTICES ISSUE: Not closing stream
            
            // PERFORMANCE ISSUE: Creating many objects
            for (int i = 0; i < 10000; i++) {
                User user = new User("id" + i, "name" + i, "email" + i);
                userCache.add(user);
            }
            
        } catch (IOException e) {
            System.out.println("Error: " + e.getMessage());
        }
    }
    
    /**
     * SECURITY ISSUE: Command injection vulnerability
     * BEST PRACTICES ISSUE: No input validation or sanitization
     */
    public void executeUserProvidedCommand(String command) throws Exception {
        // SECURITY: Direct execution without validation
        Runtime.getRuntime().exec(command);
    }
    
    /**
     * BEST PRACTICES ISSUE: No input validation
     * CODE QUALITY ISSUE: Inadequate null handling
     * MAINTAINABILITY ISSUE: Poor method name and unclear purpose
     */
    public boolean validate(String email) {
        // CODE QUALITY: Inadequate validation logic
        return email.contains("@");
    }
    
    /**
     * SECURITY ISSUE: Hardcoded database credentials
     * PERFORMANCE ISSUE: No connection pooling or timeout
     * BEST PRACTICES ISSUE: Authentication without proper validation
     */
    public User authenticateUser(String username, String password) {
        try {
            // SECURITY: Credentials hardcoded
            if (username.equals(ADMIN_USER) && password.equals(ADMIN_PASS)) {
                User admin = new User(ADMIN_USER, "Administrator", "admin@example.com");
                return admin;
            }
            
            // SECURITY ISSUE: SQL Injection
            String query = "SELECT * FROM users WHERE username = '" + username + 
                          "' AND password = '" + hashPassword(password) + "'";
            
            Statement stmt = connection.createStatement();
            ResultSet rs = stmt.executeQuery(query);
            
            if (rs.next()) {
                return new User(rs.getString("id"), rs.getString("name"), rs.getString("email"));
            }
            
        } catch (SQLException e) {
            // BEST PRACTICES ISSUE: Swallowing exception
            return null;
        }
        
        // CODE QUALITY ISSUE: Implicit null return
        return null;
    }
    
    /**
     * SECURITY ISSUE: Weak hashing algorithm (MD5 is broken)
     * PERFORMANCE ISSUE: No salt, vulnerable to rainbow tables
     */
    public String hashPassword(String password) {
        try {
            // SECURITY: MD5 is cryptographically broken
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hash = md.digest(password.getBytes());
            return String.format("%x", new java.math.BigInteger(1, hash));
        } catch (Exception e) {
            return null;
        }
    }
    
    /**
     * MAINTAINABILITY ISSUE: Overly long method (135+ lines typical for violations)
     * CODE QUALITY ISSUE: Multiple levels of nesting
     * PERFORMANCE ISSUE: N+1 query problem
     */
    public void processUserBatch(List<String> userIds) {
        Map<String, User> userMap = new HashMap<>();
        
        try {
            // PERFORMANCE: N+1 problem - query in loop
            for (String userId : userIds) {
                String query = "SELECT * FROM users WHERE id = " + userId;
                Statement stmt = connection.createStatement();
                ResultSet rs = stmt.executeQuery(query);
                
                if (rs.next()) {
                    User user = new User(
                        rs.getString("id"),
                        rs.getString("name"),
                        rs.getString("email")
                    );
                    userMap.put(userId, user);
                    
                    // SECURITY ISSUE: No validation
                    if (user.getEmail().contains("admin")) {
                        user.setAdmin(true);
                    }
                    
                    // PERFORMANCE ISSUE: Additional query per user
                    String roleQuery = "SELECT * FROM roles WHERE user_id = " + userId;
                    Statement roleStmt = connection.createStatement();
                    ResultSet roleRs = roleStmt.executeQuery(roleQuery);
                    
                    while (roleRs.next()) {
                        String role = roleRs.getString("role_name");
                        user.addRole(role);
                    }
                    
                    // BEST PRACTICES ISSUE: Not closing streams
                }
            }
            
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
    
    /**
     * SECURITY ISSUE: Reflection-based code execution
     * CODE QUALITY ISSUE: No exception handling
     * BEST PRACTICES ISSUE: No input validation
     */
    public void invokeMethod(Object obj, String methodName, Object... args) throws Exception {
        // SECURITY: Arbitrary method invocation
        Class<?> clazz = obj.getClass();
        Method method = clazz.getMethod(methodName);
        method.invoke(obj, args);
    }
    
    /**
     * BEST PRACTICES ISSUE: Using Thread instead of ExecutorService
     * PERFORMANCE ISSUE: Creating new threads repeatedly
     */
    public void processDataInThreads(List<String> data) {
        for (String item : data) {
            // BEST PRACTICES: Not using thread pool
            new Thread(() -> {
                try {
                    // Simulate processing
                    Thread.sleep(1000);
                    System.out.println("Processed: " + item);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }
    
    /**
     * MAINTAINABILITY ISSUE: No documentation of parameters/return
     * CODE QUALITY ISSUE: Unclear variable names (x, y, z)
     */
    public int complexCalculation(int x, int y, int z) {
        int a = x + y;
        int b = a * z;
        int c = b / (x - y);  // CODE QUALITY: Potential division by zero
        return c;
    }
    
    /**
     * Inner class for user data
     * BEST PRACTICES ISSUE: Mutable object with public fields
     */
    public static class User {
        public String id;
        public String name;
        public String email;
        private boolean isAdmin = false;
        private List<String> roles = new ArrayList<>();
        
        public User(String id, String name, String email) {
            this.id = id;
            this.name = name;
            this.email = email;
        }
        
        public String getEmail() {
            return email;
        }
        
        public void setAdmin(boolean admin) {
            isAdmin = admin;
        }
        
        public void addRole(String role) {
            roles.add(role);
        }
    }
    
    /**
     * USER CLASS: Stub validator
     * BEST PRACTICES ISSUE: Incomplete implementation (circular dependency)
     */
    public static class UserValidator {
        public boolean validate(User user) {
            // BEST PRACTICES ISSUE: No actual validation logic
            return user != null;
        }
    }
}
