-- Run with:  sudo mysql < create_mysql_db.sql
-- Change the password before running.
CREATE DATABASE IF NOT EXISTS maxwell_rpm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Local access (app running directly on the server)
CREATE USER IF NOT EXISTS 'rpm_user'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON maxwell_rpm.* TO 'rpm_user'@'localhost';

-- Docker access (app container connects via the docker bridge network)
CREATE USER IF NOT EXISTS 'rpm_user'@'172.%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON maxwell_rpm.* TO 'rpm_user'@'172.%';

FLUSH PRIVILEGES;
