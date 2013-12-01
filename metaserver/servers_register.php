<?php

// Description:

// SoundRTS servers call this script to register to the servers list.

// The parameters are:
// - version: the compatibility version of the server; for example: 1.0-b10o;
//   (optional: MD5 hexdigest of rules.txt, 32 characters;
//   for example: 1.1-a0-721caaf6405a987a95cdfc2d17a35437)
// - login: the login of the server;
// - ip: the IP address of the server; only numbers, no hostname;
// (optional parameter; if it is absent or empty, the IP address will be guessed by the script)
// - port: the port number of the server;
// (optional parameter; if it is absent or empty, the port number will be 2500)

// Example: http://jlpo.free.fr/soundrts/metaserver/servers_register.php?version=1.0-b10o&login=me&ip=000.000.000.000
// Other example: http://jlpo.free.fr/soundrts/metaserver/servers_register.php?version=1.1-a0-721caaf6405a987a95cdfc2d17a35437&login=me&ip=000.000.000.000
// Other example: http://jlpo.free.fr/soundrts/metaserver/servers_register.php?version=1.1-a0-721caaf6405a987a95cdfc2d17a35437&login=me&ip=000.000.000.000&port=2502

// Returns:
// - if an error occurs, "error" followed by an explanation;
// - if it works, an empty page.

// End of description.


// The code starts here...

require("config.php");

// get the parameters

$rvar_ip = getenv("REMOTE_ADDR");
import_request_variables("gP", "rvar_");
if (!preg_match("/^[a-zA-Z0-9.-]{1,52}$/", $rvar_version)) exit("error: bad version"); // 52 = 20 + 32 (optional MD5 hexdigest)
if (!preg_match("/^[a-zA-Z0-9]{1,20}$/", $rvar_login)) exit("error: bad login");
if (!preg_match("/^[0-9.]{7,40}$/", $rvar_ip)) $rvar_ip = getenv("REMOTE_ADDR");
if (!preg_match("/^[0-9]{1,5}$/", $rvar_port)) $rvar_port = "2500";

// connect to the database

$link = mysql_connect($dbhost, $dbuser, $dbpasswd)
	or die("error: connection to database failed");
mysql_select_db($dbname)
	or die("error: could not select database");

// remove the servers with this IP address from the database

$query = 'DELETE FROM soundrts_servers WHERE ip = "'.$rvar_ip.'"';
mysql_query($query) or die('error: query failed: '.mysql_error());

// insert the server in the database

$query = 'INSERT INTO soundrts_servers VALUES ('.time().',"'.$rvar_ip.'","'.$rvar_version.'","'.$rvar_login.'",'.$rvar_port.')';
mysql_query($query) or die('error: query failed: '.mysql_error());

// disconnect from the database

mysql_close($link);

?>
