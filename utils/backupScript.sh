#!/bin/bash

set -euo pipefail

BSS_NAME="${BSS_NAME:-backupScript}"
LOCK_FILE="${LOCK_FILE:-/var/run/backupScript.lock}"
PACKAGE_TMP=""
BACKUP_ALERT_SENT=false

function cleanup() {
	unset MYSQL_PWD 2>/dev/null || true
	if [[ -n "$PACKAGE_TMP" && -f "$PACKAGE_TMP" ]]; then
		rm -f "$PACKAGE_TMP"
	fi
}

trap cleanup EXIT

function alert() {
	local subject=$1
	local body=${2:-$1}
	local title="${BSS_NAME} on $(hostname): ${subject}"
	local -a apprise_args=()

	echo "[ALRT] $title"
	logger -t "$BSS_NAME" "ALERT: $title - $body" || true

	if ! command -v apprise &>/dev/null; then
		echo "[EROR] apprise not found; alert not delivered" >&2
		return 1
	fi

	apprise_args=(-n failure -t "$title" -b "$body")
	if [[ -n "${APPRISE_CONFIG:-}" ]]; then
		apprise_args+=(-c "$APPRISE_CONFIG")
	fi
	if [[ -n "${APPRISE_TAGS:-}" ]]; then
		apprise_args+=(--tag="$APPRISE_TAGS")
	fi

	apprise "${apprise_args[@]}" || {
		echo "[EROR] apprise failed to deliver alert" >&2
		return 1
	}
}

function onErr() {
	local exit_code=$?
	local line=${BASH_LINENO[0]}

	if [[ "$BACKUP_ALERT_SENT" == true ]]; then
		exit "$exit_code"
	fi

	BACKUP_ALERT_SENT=true
	alert "backup failure" "Unexpected failure at line ${line} (exit ${exit_code})"
	exit "$exit_code"
}

trap onErr ERR

function logDebug() {
	echo "[DEBG] $1"
	logger -t "$BSS_NAME" "$1" || true
}

function logInfo() {
	echo "[INFO] $1"
	logger -t "$BSS_NAME" "$1" || true
}

function logError() {
	echo "[EROR] $1" >&2
	logger -t "$BSS_NAME" "$1" || true
	BACKUP_ALERT_SENT=true
	trap - ERR
	alert "backup failure" "$1"
	exit 1
}

function checkDiskSpace() {
	local target=${1:-$PATH_PACKAGE}
	local avail_kb

	avail_kb=$(df -Pk "$target" | awk 'NR==2 {print $4}')
	if (( avail_kb < MIN_FREE_KB )); then
		logError "Insufficient disk space on $target: ${avail_kb}KB available, ${MIN_FREE_KB}KB required"
	fi
	logDebug "Disk space OK on $target: ${avail_kb}KB available"
}

function requireCommand() {
	if command -v "$1" &> /dev/null; then
		logDebug "Found required command: $1"
	else
		logError "This script requires the command: $1"
	fi
}

function init() {
	logDebug "backupScript started."
	logDebug "SHA256 hash of this script is: $(sha256sum "${BASH_SOURCE[0]}")"

	DIR_CONFIG=/etc/backupScript/
	PATH_CONFIG=$DIR_CONFIG/config.sh

	if [ -e "$PATH_CONFIG" ]; then
		logDebug "Using config file @ $PATH_CONFIG"
		# shellcheck disable=SC1090
		source "$PATH_CONFIG"
	else
		logDebug "Config file not found @ $PATH_CONFIG, using defaults"
	fi

	PATH_BACKUP=${PATH_BACKUP:-/var/backups/backupScript/staging/}
	PATH_PACKAGE=${PATH_PACKAGE:-/var/backups/backupScript/packages/}
	PATH_BACKUP_REMOTE=${PATH_BACKUP_REMOTE:-/var/backups/backupScript/remotes/}

	if [ "$(id -u)" != 0 ]; then
		logError "This script should be run as the root user."
	fi

	requireCommand tar
	requireCommand rsync
	requireCommand logger
	requireCommand sha256sum
	requireCommand par2create
	requireCommand flock

	RETENTION_DAYS=${RETENTION_DAYS:-14}
	MIN_BACKUPS_TO_KEEP=${MIN_BACKUPS_TO_KEEP:-14}
	MIN_FREE_KB=${MIN_FREE_KB:-1048576}

	if [ -z "${PATH_RUNNER:-}" ]; then
		PATH_RUNNER=$DIR_CONFIG/runner.sh
		logInfo "PATH_RUNNER is not set. The default will be used: $PATH_RUNNER"
	fi

	if [ -z "${PATH_REMOTE_RUNNER:-}" ]; then
		PATH_REMOTE_RUNNER=$DIR_CONFIG/remoteRunner.sh
	fi

	if [ ! -e "$PATH_RUNNER" ]; then
		logError "The runner file does not exist, which is used to actually run the backups. Expecting it here: $PATH_RUNNER"
	fi

	if [ -z "${PACKAGE_PREFIX:-}" ]; then
		PACKAGE_PREFIX="$(hostname)"
		logInfo "PACKAGE_PREFIX is not set, we'll use the hostname: $PACKAGE_PREFIX"
	fi

	mkdir -p "$PATH_PACKAGE"
	checkDiskSpace "$PATH_PACKAGE"

	logDebug "Cleaning the backup directory."
	rm -rf "$PATH_BACKUP"
	mkdir -p "$PATH_BACKUP"
}

# Opposite of init.
function smite() {
	logDebug "Smite'ing"

	rotate
	package

	logDebug "Backup script has finished."
}

function package() {
	local timestamp archive_name backup_dir archive_name_base archive_path checksum_path manifest_path

	timestamp="$(date +%Y-%m-%d_%H%M%S)"
	archive_name_base="${PACKAGE_PREFIX}.backup.${timestamp}"
	backup_dir="$PATH_PACKAGE/${archive_name_base}"
	archive_name="${archive_name_base}.bz2"
	archive_path="$backup_dir/$archive_name"
	checksum_path="$archive_path.sha256"
	manifest_path="$backup_dir/manifest.txt"

	logDebug "Making package in: $backup_dir"

	mkdir -p "$PATH_PACKAGE"
	checkDiskSpace "$PATH_PACKAGE"
	cd "$PATH_BACKUP" || logError "Cannot cd to $PATH_BACKUP"

	if [[ -z "$(find . -mindepth 1 -print -quit 2>/dev/null)" ]]; then
		# Empty staging is OK when this run still pulls remotes afterward.
		if [[ -e "${PATH_REMOTE_RUNNER:-}" ]]; then
			logInfo "Staging directory is empty; skipping local package (remote backups will still run)"
			return 0
		fi
		logError "Staging directory is empty; nothing to package"
	fi

	mkdir -p "$backup_dir"
	PACKAGE_TMP="$backup_dir/.${archive_name}.tmp"
	tar cavf "$PACKAGE_TMP" .
	tar tf "$PACKAGE_TMP" >/dev/null
	mv -f "$PACKAGE_TMP" "$archive_path"
	PACKAGE_TMP=""

	(
		cd "$backup_dir"
		sha256sum "$archive_name" > "$archive_name.sha256"
		sha256sum -c "$archive_name.sha256"
	)

	{
		echo "timestamp=$timestamp"
		echo "hostname=$(hostname)"
		echo "package_prefix=$PACKAGE_PREFIX"
		echo "archive=$archive_name"
		echo "sha256=$(awk '{print $1}' "$checksum_path")"
		echo "script_sha256=$(sha256sum "${BASH_SOURCE[0]}" | awk '{print $1}')"
		echo "files:"
		tar tf "$archive_path" | sed 's/^/  /'
	} > "$manifest_path"

	(
		cd "$backup_dir"
		par2create -r10 -a "$archive_name" "${archive_name}.par2" \
			"$archive_name" "${archive_name}.sha256" manifest.txt
	)

	logInfo "Package created at $backup_dir"
}

function rotate() {
	local -a dirs=()
	local dir count legacy

	logDebug "Rotating backups (retention=${RETENTION_DAYS} days, min_keep=${MIN_BACKUPS_TO_KEEP})."

	mkdir -p "$PATH_PACKAGE"

	while IFS= read -r -d '' legacy; do
		logDebug "Removing legacy flat backup: $legacy"
		rm -f "$legacy"
	done < <(find "$PATH_PACKAGE" -maxdepth 1 -type f -name '*.backup.*.bz2' -mtime +"${RETENTION_DAYS}" -print0)

	mapfile -t dirs < <(find "$PATH_PACKAGE" -mindepth 1 -maxdepth 1 -type d -name "${PACKAGE_PREFIX}.backup.*" | sort)
	count=${#dirs[@]}

	for dir in "${dirs[@]}"; do
		if (( count <= MIN_BACKUPS_TO_KEEP )); then
			break
		fi
		if [[ -n "$(find "$dir" -maxdepth 0 -mtime +"${RETENTION_DAYS}" -print -quit)" ]]; then
			logDebug "Removing old backup: $dir"
			rm -rf "$dir"
			((count--)) || true
		fi
	done

	logDebug "Finished rotation ($count backup(s) retained)."
}

# @param $1 username
# @param $2 password
function bkpMySqlDatabase() {
	requireCommand mysql
	requireCommand mysqldump

	logDebug "Backing up MySQL Databases"

	local user=$1
	local pass=$2
	local database
	local tmp dest first_line

	export MYSQL_PWD="$pass"
	DBS="$(mysql -u "$user" -Bse 'SHOW DATABASES')"

	for database in $DBS; do
		case $database in
			information_schema|performance_schema|mysql|sys|logs)
				continue
				;;
		esac

		mkdir -p "$PATH_BACKUP/databases/"
		tmp="$PATH_BACKUP/databases/${database}.sql.tmp"
		dest="$PATH_BACKUP/databases/${database}.sql"

		mysqldump --single-transaction -u "$user" "$database" > "$tmp"

		if [[ ! -s "$tmp" ]]; then
			rm -f "$tmp"
			logError "MySQL dump is empty for database: $database"
		fi
		if ! head -20 "$tmp" | grep -qE '^-- (MySQL|MariaDB) dump'; then
			first_line=$(head -1 "$tmp")
			rm -f "$tmp"
			logError "MySQL dump does not look valid for database: $database (first line: $first_line)"
		fi

		mv -f "$tmp" "$dest"
		logDebug "MySQL dump completed for: $database"
	done
}

# @param $1 The directory to backup
# @param $2 The directory under PATH_BACKUP which will hold this
# @param $3 Extra arguments to pass to rsync (optional)
function bkpDirectory() {
	local source=$1
	local dest_subdir=$2
	local dest_path="$PATH_BACKUP/$dest_subdir"

	logDebug "Backing up directory: $source"

	if [[ ! -e "$source" ]]; then
		logError "Backup source does not exist: $source"
	fi

	if [[ -d "$source" && "${source: -1}" != "/" ]]; then
		source="${source}/"
	fi

	cd "$PATH_BACKUP" || logError "Cannot cd to $PATH_BACKUP"
	mkdir -p "$dest_path"

	if [ -n "${3:-}" ]; then
		# shellcheck disable=SC2086
		rsync -av "$source" "${dest_path}/" $3
	else
		rsync -av "$source" "${dest_path}/"
	fi
}

# @param $1 The file to backup.
# @param $2 The directory to put the backed up file in (under $PATH_BACKUP)
function bkpFile() {
	logDebug "Backing up file: $1"

	if [[ ! -e "$1" ]]; then
		logError "Backup source does not exist: $1"
	fi

	if [ -z "${2:-}" ]; then
		cp -a -H -v "$1" "$PATH_BACKUP/"
	else
		if [ ! -e "$PATH_BACKUP/$2" ]; then
			mkdir -p "$PATH_BACKUP/$2"
		fi

		cp -a -H -v "$1" "$PATH_BACKUP/$2/"
	fi
}

# Select the latest backup directory per calendar day from a list of basenames.
# Sets the array named by $2 to the chosen directory names.
function bkpRemoteSelectLatestPerDay() {
	local -n _dirs=$1
	local -n _selected=$2
	local -A latest_time=()
	local -A latest_name=()
	local dir date time day

	_selected=()
	for dir in "${_dirs[@]}"; do
		if [[ $dir =~ \.backup\.([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{6})$ ]]; then
			date=${BASH_REMATCH[1]}
			time=${BASH_REMATCH[2]}
			if [[ -z "${latest_time[$date]:-}" || ${latest_time[$date]} < $time ]]; then
				latest_time[$date]=$time
				latest_name[$date]=$dir
			fi
		else
			logDebug "Skipping unrecognized remote backup directory: $dir"
		fi
	done

	for day in "${!latest_name[@]}"; do
		_selected+=("${latest_name[$day]}")
	done
}

# @param $1 Remote host (e.g. user@host or host)
# @param $2 Remote package directory (optional, default: /var/backups/backupScript/packages)
function bkpRemote() {
	requireCommand ssh

	local remote_host=$1
	local remote_path=${2:-/var/backups/backupScript/packages}
	local host_key dest remote_spec archive_name dir day today remote_list
	local has_today=false
	local -a remote_dirs=() selected_dirs=()

	remote_path=${remote_path%/}
	host_key="${remote_host##*@}"
	dest="${PATH_BACKUP_REMOTE%/}/${host_key}"
	remote_spec="${remote_host}:${remote_path}"
	today="$(date -u +%Y-%m-%d)"

	logInfo "Pulling remote backups from $remote_spec into $dest"

	mkdir -p "$dest"
	checkDiskSpace "$dest"

	if ! remote_list=$(ssh -o BatchMode=yes "$remote_host" \
		"find '${remote_path}' -mindepth 1 -maxdepth 1 -type d -name '*.backup.*' -printf '%f\n' 2>/dev/null"); then
		alert "remote unreachable (${host_key})" \
			"Failed to connect to ${remote_spec}"
		return 1
	fi

	if [[ -z "$remote_list" ]]; then
		alert "no remote backups (${host_key})" \
			"No backup directories found on ${remote_spec}"
		return 1
	fi

	remote_dirs=()
	while IFS= read -r dir; do
		[[ -n "$dir" ]] && remote_dirs+=("$dir")
	done < <(sort <<< "$remote_list")

	if ((${#remote_dirs[@]} == 0)); then
		alert "no remote backups (${host_key})" \
			"No backup directories found on ${remote_spec}"
		return 1
	fi

	for dir in "${remote_dirs[@]}"; do
		if [[ $dir =~ \.backup\.${today}_[0-9]{6}$ ]]; then
			has_today=true
			break
		fi
	done

	if [[ "$has_today" != true ]]; then
		alert "no daily remote backup (${host_key})" \
			"No backup for ${today} (UTC) found on ${remote_spec}"
		return 1
	fi

	bkpRemoteSelectLatestPerDay remote_dirs selected_dirs
	logDebug "Selected ${#selected_dirs[@]} backup(s) (latest per day) from ${#remote_dirs[@]} on $host_key"

	for dir in "${selected_dirs[@]}"; do
		if [[ ! $dir =~ \.backup\.([0-9]{4}-[0-9]{2}-[0-9]{2})_[0-9]{6}$ ]]; then
			logError "Cannot parse date from backup directory: $dir"
		fi
		day=${BASH_REMATCH[1]}

		for local_dir in "$dest"/*.backup."${day}"_*; do
			[[ -e "$local_dir" ]] || continue
			if [[ "$(basename "$local_dir")" != "$dir" ]]; then
				logDebug "Removing superseded same-day local backup: $local_dir"
				rm -rf "$local_dir"
			fi
		done

		logDebug "Syncing $remote_spec/$dir/"
		rsync -av "${remote_spec}/${dir}/" "${dest}/${dir}/" \
			|| logError "Failed to sync ${remote_spec}/${dir}/"

		archive_name="${dir}.bz2"
		if [[ -f "${dest}/${dir}/${archive_name}.sha256" ]]; then
			(
				cd "${dest}/${dir}"
				sha256sum -c "${archive_name}.sha256"
			) || logError "Checksum verification failed for ${host_key}/${dir}"
			logDebug "Checksum verified for $host_key/$dir"
		fi
	done

	logInfo "Remote backup pull completed for $host_key"
}

function runRemoteRunner() {
	if [[ ! -e "$PATH_REMOTE_RUNNER" ]]; then
		logDebug "No remote runner at $PATH_REMOTE_RUNNER (skipping)"
		return 0
	fi

	logInfo "Running remote runner @ $PATH_REMOTE_RUNNER"
	set +e
	# shellcheck disable=SC1090
	source "$PATH_REMOTE_RUNNER"
	local rc=$?
	set -e

	if (( rc != 0 )); then
		logInfo "Remote runner finished with exit code ${rc} (local backup already packaged)"
	fi
}

function showHelp() {
	cat <<'EOF'
backupScript — staging backup tool

Run without arguments to:
  1. Execute /etc/backupScript/runner.sh (stage local backup data)
  2. Package and rotate local backups
  3. Execute /etc/backupScript/remoteRunner.sh if present (pull remote backups)

Configuration: /etc/backupScript/config.sh
Local runner:   /etc/backupScript/runner.sh
Remote runner:  /etc/backupScript/remoteRunner.sh (optional)

Paths (defaults, overridable in config.sh):
  PATH_BACKUP         /var/backups/backupScript/staging/     (staging)
  PATH_PACKAGE        /var/backups/backupScript/packages/    (local archives)
  PATH_BACKUP_REMOTE  /var/backups/backupScript/remotes/     (pulled remotes)

Backup functions for use in runner.sh:

  bkpMySqlDatabase USER PASS
      Dump all user databases to PATH_BACKUP/databases/.
      Skips information_schema, performance_schema, mysql, sys, and logs.

  bkpDirectory SOURCE DEST [RSYNC_ARGS...]
      Rsync SOURCE contents into PATH_BACKUP/DEST/.
      If SOURCE is a directory, its contents are copied (trailing slash added).

  bkpFile FILE [DEST]
      Copy FILE into PATH_BACKUP/, or into PATH_BACKUP/DEST/ if DEST is set.

Use remoteRunner.sh (not runner.sh) for remote pulls so local packaging is
not blocked by remote failures:

  bkpRemote HOST [REMOTE_PATH]
      Pull backup archives from a remote host via rsync over SSH.
      HOST is user@host or host. REMOTE_PATH defaults to
      /var/backups/backupScript/packages.
      Stores under PATH_BACKUP_REMOTE/HOST/ — one subdirectory per remote.
      Syncs the latest archive per calendar day only; does not delete local
      copies when the origin rotates. Alerts if the remote is unreachable,
      has no backups, or is missing today's backup (UTC date).

Example runner.sh:

  bkpMySqlDatabase backupuser "$DB_PASS"
  bkpDirectory /etc/nginx nginx
  bkpFile /etc/letsencrypt/live/example.com/fullchain.pem ssl

Example remoteRunner.sh:

  bkpRemote root@webserver

Options:

  --test-alert      Send a test alert via apprise (loads /etc/backupScript/config.sh)
  -h, --help        Show this help

EOF
}

function loadAlertConfig() {
	local config=/etc/backupScript/config.sh

	if [[ -e "$config" ]]; then
		# shellcheck disable=SC1090
		source "$config"
	fi
}

function testAlert() {
	loadAlertConfig
	trap - ERR

	echo "[INFO] Sending test alert..."
	if alert "test alert" \
		"This is a test alert from backupScript on $(hostname) at $(date -Is). If you received this, apprise is configured correctly."; then
		echo "[INFO] Test alert sent"
		exit 0
	fi

	echo "[EROR] Test alert failed" >&2
	exit 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	case "${1:-}" in
		-h|--help|help)
			showHelp
			exit 0
			;;
		--test-alert)
			testAlert
			;;
	esac

	exec 9>"$LOCK_FILE"
	if ! flock -n 9; then
		loadAlertConfig
		trap - ERR
		alert "concurrent run blocked" \
			"Another backupScript instance is already running (lock: ${LOCK_FILE})"
		exit 1
	fi

	init
	# shellcheck disable=SC1090
	source "$PATH_RUNNER"
	smite
	runRemoteRunner
fi
