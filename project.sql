-- Create the database
CREATE DATABASE TrafficManagementSystem;
USE TrafficManagementSystem;

-- Users Table
CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Role ENUM('Administrator', 'Commuter') NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    Password VARCHAR(255) NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE, -- Soft delete
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Police Stations Table
CREATE TABLE PoliceStations (
    StationID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Location VARCHAR(255) NOT NULL,
    ContactNumber VARCHAR(15),
    IsActive BOOLEAN DEFAULT TRUE, -- Soft delete
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE Officers (
    OfficerID INT AUTO_INCREMENT PRIMARY KEY,               -- Unique ID for each officer
    Name VARCHAR(100) NOT NULL,                             -- Officer's name
    OfficerRank ENUM('Inspector', 'Sub-Inspector') NOT NULL, -- Officer's rank
    StationID INT NOT NULL,                                 -- Linked Police Station
    ContactNumber VARCHAR(15),                              -- Optional contact number
    IsActive BOOLEAN DEFAULT TRUE,                          -- Soft delete support
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,          -- Auto-set creation time
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
              ON UPDATE CURRENT_TIMESTAMP,                  -- Auto-update modification time
    FOREIGN KEY (StationID) REFERENCES PoliceStations(StationID) ON DELETE CASCADE -- Cascade delete
);


-- Vehicles Table
CREATE TABLE Vehicles (
    VehicleID INT AUTO_INCREMENT PRIMARY KEY,
    RegistrationNumber VARCHAR(50) UNIQUE NOT NULL,
    Type ENUM('Car', 'Truck', 'Motorcycle') NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_vehicle_reg (RegistrationNumber) -- Index for faster searches
);

-- Traffic Signals Table
CREATE TABLE TrafficSignals (
    SignalID INT AUTO_INCREMENT PRIMARY KEY,
    Location VARCHAR(255) NOT NULL,
    CurrentLight ENUM('Red', 'Yellow', 'Green') NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE TrafficViolations (
    ViolationID INT AUTO_INCREMENT PRIMARY KEY,
    VehicleID INT NOT NULL,
    ViolationType ENUM('Speeding', 'Red Light Jump', 'No Helmet', 'Illegal Parking') NOT NULL,
    FineAmount DECIMAL(10, 2) NOT NULL,
    OfficerID INT,  -- Make OfficerID nullable to allow it to be set to NULL
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID) ON DELETE CASCADE,
    FOREIGN KEY (OfficerID) REFERENCES Officers(OfficerID) ON DELETE SET NULL  -- Allow OfficerID to be set to NULL
);


-- Optional: Roads/Routes Table
CREATE TABLE Roads (
    RoadID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    StartPoint VARCHAR(100),
    EndPoint VARCHAR(100),
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Add Status column to TrafficViolations table if it doesn't exist
ALTER TABLE TrafficViolations 
ADD COLUMN Status ENUM('Pending', 'Paid', 'Cancelled') DEFAULT 'Pending';

-- First, drop the trigger if it already exists
DROP TRIGGER IF EXISTS after_violation_status_update;

-- Create the trigger
DELIMITER //
CREATE TRIGGER after_violation_status_update 
AFTER UPDATE ON TrafficViolations
FOR EACH ROW
BEGIN
    IF NEW.Status = 'Cancelled' THEN
        -- Delete the violation
        DELETE FROM TrafficViolations WHERE ViolationID = NEW.ViolationID;
    END IF;
END//
DELIMITER ;

ALTER TABLE Officers 
ADD COLUMN Status ENUM('Active', 'Suspended') DEFAULT 'Active';

-- Rename the column from VehicleType to Type if it exists
ALTER TABLE Vehicles 
CHANGE COLUMN VehicleType Type VARCHAR(50);

ALTER TABLE Officers 
MODIFY COLUMN Status ENUM('Active', 'Suspended', 'Retired') DEFAULT 'Active';

CREATE TABLE OfficerTransfers (
    TransferID INT PRIMARY KEY AUTO_INCREMENT,
    OfficerID INT,
    FromStationID INT,
    ToStationID INT,
    TransferReason TEXT,
    TransferDate DATETIME,
    FOREIGN KEY (OfficerID) REFERENCES Officers(OfficerID),
    FOREIGN KEY (FromStationID) REFERENCES PoliceStations(StationID),
    FOREIGN KEY (ToStationID) REFERENCES PoliceStations(StationID)
);

-- Drop existing foreign key constraint
ALTER TABLE OfficerTransfers 
DROP FOREIGN KEY officertransfers_ibfk_1;

-- Add new foreign key constraint with CASCADE
ALTER TABLE OfficerTransfers
ADD CONSTRAINT officertransfers_ibfk_1 
FOREIGN KEY (OfficerID) 
REFERENCES Officers(OfficerID) 
ON DELETE CASCADE;

-- Add new foreign key constraints with CASCADE
ALTER TABLE OfficerTransfers
ADD CONSTRAINT officertransfers_ibfk_2 
FOREIGN KEY (FromStationID) 
REFERENCES PoliceStations(StationID) 
ON DELETE CASCADE,
ADD CONSTRAINT officertransfers_ibfk_3 
FOREIGN KEY (ToStationID) 
REFERENCES PoliceStations(StationID) 
ON DELETE CASCADE;