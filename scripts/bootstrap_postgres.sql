CREATE ROLE bf_user WITH LOGIN PASSWORD 'bf_password';

CREATE DATABASE borderflow_depot OWNER bf_user;
CREATE DATABASE borderflow_border OWNER bf_user;
CREATE DATABASE borderflow_port OWNER bf_user;
CREATE DATABASE borderflow_destination OWNER bf_user;
