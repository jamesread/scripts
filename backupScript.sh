#!/bin/bash

function requireCommand() {
	if which $1 &> /dev/null; then
		logDebug "Found required command: $1"
	else
		logError "This script requires the command: $1"
	fi
}

function init() {
	DIR_CONFIG=/etc/backupScript/
	PATH_CONFIG=$DIR_CONFIG/settings.sh

	logDebug "backupScript started."
	logDebug "SHA1 Hash of this script is: `sha1sum $0`"

	if [ ! "`whoami`" = 'root' ]; then
		logError "This script should be run as the root user."
	fi

	requireCommand zip
	requireCommand rsync
	requireCommand logger

	if [ -e "$PATH_CONFIG" ]; then
		logDebug "Using config file @ $PATH_CONFIG"
		source "$PATH_CONFIG"
	else 
		logError "Cannot source the configuration file, was expecting it here: $PATH_CONFIG"
	fi

	if [ -z "$PATH_BACKUP" ]; then
		logError "PATH_BACKUP has not been specified in the config."
	else 
		if [ ! -e "$PATH_BACKUP" ]; then 
			logDebug "The PATH_BACKUP does not exist! I will create it ($PATH_BACKUP) " 
			mkdir -p "$PATH_BACKUP"
		else 
			logDebug "The backup path looks okay ($PATH_BACKUP) "
		fi

		logDebug "Cleaning the backup directory."
		rm -rf "$PATH_BACKUP"
		mkdir -p "$PATH_BACKUP"
	fi

	if [ -z "$PATH_RUNNER" ]; then
		PATH_RUNNER=$DIR_CONFIG/runner.sh
		logInfo "PATH_RUNNER is not set. The default will be used: $PATH_CONFIG "
	fi

	if [ ! -e "$PATH_RUNNER" ]; then
		logError "The backup.sh file does not exist, which is used to actually run the backups. Expecting it here: $PATH_RUNNER "
	fi;

	if [ -z "$PACKAGE_PREFIX" ]; then
		logInfo "PACKAGE_PREFIX is not set, we'll use the hostname: `hostname`"
		PACKAGE_PREFIX=`hostname`
	fi
}

# Opposite of init.
function smite() {
	logDebug "Smite'ing"

	rotate
	package
	
	logDebug "Backup script has finished."
}

function logDebug() {
	echo "[DEBG] $1"
	logger -t "$BSS_NAME" "$1"
}

function logInfo() {
	echo "[INFO] $1 "
	logger -t "$BSS_NAME" "$1"
}

function logError() {
	echo "[EROR] $1"
	logger -t "$BSS_NAME" "$1"
	exit
}

function package() {
	if [ -z "$PATH_PACKAGE" ]; then
		logDebug "PATH_PACKAGE has not been specified, so I wont make a package."
	else 
		if [ ! -e "$PATH_PACKAGE" ]; then
			logDebug "PATH_PACKAGE has been specified, but does not exist. I dont want to create it."
		else 
			logDebug "Making package to: ($PATH_PACKAGE)"

			cd "$PATH_BACKUP"
			zip -rv "$PATH_PACKAGE/$PACKAGE_PREFIX.backup.`date +%Y-%m-%d`.zip" "."
		fi
	fi
}

function rotate() {
	logDebug "Rotating backups."
	
	cd "$PATH_PACKAGE"
	find -mtime +3 | xargs rm -rf 
	
	logDebug "Finished rotation."
}

# @param $1 username
# @param $2 password
function bkpMySqlDatabase() {
	requireCommand mysql

	logDebug "Backing up MySQL Databases"

	DBS="$(mysql -u $1 -p"$2" -Bse 'SHOW DATABASES')"

	for database in $DBS; do
		if [ "$database" = "information_schema" ]; then continue; fi;
		if [ "$database" = "logs" ]; then continue; fi;

		mkdir -p "$PATH_BACKUP/databases/"
		mysqldump --compress -u $1 -p$2 "$database" > "$PATH_BACKUP/databases/$database.sql"

		if [ $? -eq 0 ]; then
			logDebug "MySQL dump exited successfully after backing up: $database"
		else 
			logDebug "MySQL dump exited with error: $? after backing up: $database" 
		fi
	done
}

# @param $1 The path to the SVN repo
# @param $2 The name of the backup
function bkpSvn() {
	requireCommand svnadmin

	logDebug "Backing up SVN repo: $1 "	

	svnadmin dump "$1" > "$PATH_BACKUP/$2.svndump" | logDebug
}

# @param $1 The directory to backup
# @param $2 The directory under PATH_BACKUP which will hold this
# @param $3 Extra arguments to pass to rsync
function bkpDirectory() {
	logDebug "Backing up directory: $1"
	cd "$PATH_BACKUP"
	mkdir -p $2
	
	rsync -av $1 "$PATH_BACKUP/$2" $3 | logDebug
}

# @param $1 The file to backup.
# @param $2 The directory to put the backed up file in (under $PATH_BACKUP)
function bkpFile() {
	logDebug "Backing up file: $1" 

	if [ -z "$2" ]; then
			cp -a -H -u -v "$1" "$PATH_BACKUP/"
	else 
			if [ ! -e "$PATH_BACKUP/$2" ]; then
				mkdir -p "$PATH_BACKUP/$2"
			fi

			cp -a -H -u -v "$1" "$PATH_BACKUP/$2/"
	fi
}

init
source "$PATH_RUNNER"
smite
