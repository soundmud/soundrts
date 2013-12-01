<?php

// Description:

// This script will create the table required by the metaserver.
// 1. Edit the config.php file;
// 2. Upload and run this script once;
// 3. Remove this script from the metaserver.

// No parameter.

// Returns:
// - if an error occurs, "error" followed by an explanation;
// - if it works, an empty page.

// End of description.


// The code starts here...

require("config.php");

// connect to the database

$link = mysql_connect($dbhost, $dbuser, $dbpasswd)
	or die("error: connexion to database failed");
mysql_select_db($dbname)
	or die("error: could not select database");

// create the "soundrts_servers" table

$query = "CREATE TABLE soundrts_servers (time INT UNSIGNED NOT NULL, ip VARCHAR(40) NOT NULL, version VARCHAR(52) NOT NULL, login VARCHAR(20) NOT NULL, port INT UNSIGNED NOT NULL)";  // 52 = 20 + 32 (optional MD5 hexdigest)
$result = mysql_query($query)
	or die('error: query failed: '.mysql_error());

// disconnect from the database

mysql_close($link);

?>
