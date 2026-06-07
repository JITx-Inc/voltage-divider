#!/bin/bash
set -Eeuo pipefail

THISDIR="$(dirname $0)"
TEMPLATEFILE="${THISDIR}/slack-template.jq"

# Defaulted env var inputs - can override if necessary
: "${CHANNEL:=C04E41FMKLY}"
: "${COLOR:=#ffff00}"
: "${EMOJI:=:grey_question:}"
: "${DESC:=Unknown}"
: "${VER:=unknown}"
: "${BRANCH:=unknown}"
: "${RESULT:=unknown}"
: "${GHLOG:=}"
: "${URL:=https://github.com/JITx-Inc}"

if [ "$RESULT" == "success" ] ; then
  RESULT="passed"
  COLOR="#00ff00"
  EMOJI=":white_check_mark:"
elif [ "$RESULT" == "failure" ] ; then
  RESULT="FAILED"
  COLOR="#ff0000"
  EMOJI=":fire:"
fi

# render the template with substitutions
jq -cn \
      --arg channel "${CHANNEL}" \
      --arg color "${COLOR}" \
      --arg emoji "${EMOJI}" \
      --arg desc "${DESC}" \
      --arg ver "${VER}" \
      --arg branch "${BRANCH}" \
      --arg result "${RESULT}" \
      --arg ghlogtype "${GHLOGTYPE:0:2900}" \
      --arg ghlogtest "${GHLOGTEST:0:2900}" \
      --arg ghlogbuild "${GHLOGBUILD:0:2900}" \
      --arg ghlogpublish "${GHLOGPUBLISH:0:2900}" \
      --arg url "${URL}" \
      -f "${TEMPLATEFILE}"
