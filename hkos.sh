#!/bin/bash

if [[ "$(uname -a)" =~ 'Darwin' ]]; then
	export DYLD_FALLBACK_LIBRARY_PATH="/opt/brew/lib:/usr/lib"
fi

HKOS_HOME="${HKOS_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"}"
HKOS_CONFIG_DIR="${HKOS_CONFIG_DIR:-$HKOS_HOME/config}"

export PYTHONPATH=$HKOS_HOME
export HKOS_HOME
export HKOS_CONFIG_DIR

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]
then
	APP="$1"; shift
	exec ${PYTHONBIN:-python3} "$HKOS_HOME/apps/${APP}.py" "$@"
fi
